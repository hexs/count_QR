from flask import Flask, render_template, Response, request, jsonify
import cv2
import numpy as np

app = Flask(__name__)

click_position = None


def gen_frames(data):
    global click_position
    while True:
        img = data['img']

        if img is None:
            img = np.zeros((480, 640, 3), np.uint8)

        if click_position:
            cv2.putText(img, f'{click_position}', click_position, 1, 0.5, (0, 255, 0), 2)
            click_position = None

        ret, buffer = cv2.imencode('.jpg', img)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/')
def index():
    data = app.config['data']
    count = {
        'qr': 0,
        'mark': 0,
        'socket_qr_output': '-',
        'socket_mk_output': '-',
        'socket_rs_output': '-'
    }
    if data['count']:
        count['qr'] = data['count'].get('0 qr', {}).get('count', 0)
        count['mark'] = data['count'].get('1 mark', {}).get('count', 0)

        data['socket_qr_output'] = data['count'].get('0 qr', {}).get('count', 0)
        data['socket_mk_output'] = data['count'].get('1 mark', {}).get('count', 0)
        data['socket_rs_output'] = count['qr'] if count['qr'] == count['mark'] else 'NG'
    return render_template('index.html', count=count)


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(app.config['data']),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/click', methods=['POST'])
def handle_click():
    global click_position
    data = request.json
    click_position = (int(data['x']), int(data['y']))
    return 'OK'


@app.route('/get_counts')
def get_counts():
    data = app.config['data']
    counts = {
        'qr': data['count'].get('0 qr', {}).get('count', 0) if data['count'] else 0,
        'mark': data['count'].get('1 mark', {}).get('count', 0) if data['count'] else 0,
        'socket_qr_output': data['socket_qr_output'],
        'socket_mk_output': data['socket_mk_output'],
        'socket_rs_output': data['socket_rs_output'],
        'socket_status': data['socket status'],
        'count': data['count'] is not None
    }
    return jsonify(counts)


def run_server(data):
    app.config['data'] = data
    ipv4 = data['config']['ipv4']
    port = data['config']['webserver_port']
    app.run(ipv4, port, debug=False, use_reloader=False)


def capture(data):
    from hexss.image import get_image
    import time
    import numpy as np
    import cv2

    url = cv2.VideoCapture('241015-141410.mp4')
    url = data['config']['url_image']
    while data['play']:
        img = get_image(url)
        img[0:768, 0:200] = np.zeros((768, 200, 3), np.uint8)
        img[0:768, 1024 - 150:1024] = np.zeros((768, 150, 3), np.uint8)

        data['img'] = img.copy()
        # data['img'] = np.zeros(())
        # (480, 640, 3) print(data['img'].shape)
        time.sleep(1 / 30)


def predict(data):
    from hexss.detector import ObjectDetector

    detector = ObjectDetector("best.pt")
    while data['play']:
        if data.get('img') is not None:
            results = detector.detect(data['img'])
            data['results'] = results
            data['count'] = detector.count


def sock(data):
    import socket
    import time
    import subprocess

    def close_port(ip, port):
        try:
            result = subprocess.run(
                f'''for /f "tokens=5" %a in ('netstat -ano ^| findstr {ip}:{port}') do taskkill /F /PID %a''',
                shell=True, capture_output=True, text=True)
            print(result.stdout)
        except Exception as e:
            print(f"Error closing port: {e}")

    while data['play']:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        while True:
            try:
                server_socket.bind((data['config']['ipv4'], data['config']['socket_port_connect_PLC']))
                break
            except OSError as e:
                print(f"Binding failed: {e}")
                close_port('192.168.225.137', 9000)
                time.sleep(1)

        server_socket.listen(2)
        data['socket status'] = "Server Waiting for connection..."
        conn, address = server_socket.accept()
        data['socket status'] = f"Connection from: {address}"

        while True:
            socket_data = conn.recv(1024)
            print(socket_data)
            print(socket_data.decode())

            if not socket_data:
                data['socket status'] = "Connection closed"
                break

            qr = data['count'].get('0 qr', {}).get('count', 100)
            mark = data['count'].get('1 mark', {}).get('count', 100)
            num = qr if qr == mark else 100
            if num == 0:
                num = 101

            data['socket_qr_output'] = data['count'].get('0 qr', {}).get('count', 0)
            data['socket_mk_output'] = data['count'].get('1 mark', {}).get('count', 0)
            data['socket_rs_output'] = "NG" if num >= 100 else num
            conn.send(num.to_bytes(2, byteorder='little'))
            print(f"send {num}")
        conn.close()
        server_socket.close()


def show(data):
    import json
    import cv2
    from hexss.image.func import numpy_to_pygame_surface
    import pygame
    from pygame import Rect
    from pygame_gui import UIManager
    from pygame_gui.elements import UITextBox

    pygame.init()
    pygame.display.set_caption('Count QR Code')
    window_size = (860, 510)
    display = pygame.display.set_mode(window_size)
    manager = UIManager(window_size)
    background = pygame.Surface(window_size)
    background.fill(manager.ui_theme.get_colour('dark_bg'))

    socket_status_label = UITextBox('-', Rect(0, 480, 640, 30), manager)

    qr_label = UITextBox('QR Code :', Rect(640, 0, 220, 30), manager)
    mk_label = UITextBox('Mark :', Rect(640, 30, 220, 30), manager)

    socket_qr_output_label = UITextBox('QR Code :', Rect(640, 420, 220, 30), manager)
    socket_mk_output_label = UITextBox('Mark :', Rect(640, 450, 220, 30), manager)
    socket_rs_output_label = UITextBox('Result :', Rect(640, 480, 220, 30), manager)

    rect = Rect(0, 0, 500, 120)
    rect.center = (window_size[0] / 2, window_size[1] / 2)
    loading_panel = UITextBox(f"<font color='#FFAA00' size=7>loading...</font><br>", rect, manager)

    clock = pygame.time.Clock()
    colors = [(255, 0, 255), (0, 255, 255), (255, 255, 0)]

    while data['play']:
        time_delta = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                data['play'] = False
            manager.process_events(event)

        manager.update(time_delta)
        display.blit(background, (0, 0))

        if data.get('img') is not None:
            img = data['img'].copy()
            for result in data['results']:
                xyxy = result['xyxy']
                cls = result['cls']
                x1y1 = xyxy[:2].astype(int)
                x2y2 = xyxy[2:].astype(int)
                cv2.rectangle(img, tuple(x1y1), tuple(x2y2), colors[cls], 2)

            socket_status_label.set_text(data['socket status'])
            if data['count']:
                loading_panel.kill()

                qr = data['count'].get('0 qr', {}).get('count', 0)
                mark = data['count'].get('1 mark', {}).get('count', 0)
                qr_label.set_text(f'QR Code : {qr}')
                mk_label.set_text(f'Mark : {mark}')

            socket_qr_output_label.set_text(f'{data["socket_qr_output"]}')
            socket_mk_output_label.set_text(f'{data["socket_mk_output"]}')
            socket_rs_output_label.set_text(f'{data["socket_rs_output"]}')
            display.blit(numpy_to_pygame_surface(cv2.resize(img, (640, 480))), (0, 0))

        manager.draw_ui(display)
        pygame.display.update()

    pygame.quit()


if __name__ == '__main__':
    from hexss.threading import Multithread
    import hexss
    from hexss.json import json_load
    import time

    config = json_load('config.json',
                       {
                           "ipv4": hexss.get_ipv4(),
                           "socket_port_connect_PLC": 9000,
                           "webserver_port": 5555,
                           "url_image": 'http://192.168.123.122:2000/image?source=video_capture&id=0'

                       }, True)
    m = Multithread()
    data = {
        'config': config,
        'play': True,
        'socket status': '-',
        'socket_qr_output': '-',
        'socket_mk_output': '-',
        'socket_rs_output': '-',
        'img': None,
        'results': [],
        'count': None
    }
    m.add_func(show, (data,))
    m.add_func(predict, (data,))
    m.add_func(capture, (data,))
    m.add_func(sock, (data,), join=False)
    m.add_func(run_server, (data,))

    m.start()
    try:
        while data['play']:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        data['play'] = False
        m.join()
