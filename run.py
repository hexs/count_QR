import time
from datetime import datetime, timedelta
import cv2
import numpy as np
from hexss.json import json_load, json_update


def capture(data):
    from hexss.image import get_image
    import time
    import cv2
    from random import randint

    url = data['config']['url_image']
    while data['play']:
        img = get_image(url)
        img[0:768,0:200] = np.zeros((768,200,3),np.uint8)
        img[0:768,1024-150:1024] = np.zeros((768,150,3),np.uint8)


        if img is None:
            img = np.full(
                (480, 640, 3),
                (randint(100, 255), randint(100, 255), randint(100, 255)),
                np.uint8
            )
            cv2.putText(img, 'Error loading image from URL', (50, 100), 1, 2, (0, 0, 0), 2)
        data['img'] = img.copy()
        time.sleep(1 / 30)


def predict(data):
    from hexss.detector import ObjectDetector

    detector = ObjectDetector("best.pt")
    while data['play']:
        if data.get('img') is not None:
            results = detector.detect(data['img'])
            data['results'] = results
            data['count'] = detector.count


def draw_elements(data):
    colors = [(255, 0, 255), (0, 255, 255), (255, 255, 0)]
    while data['play']:
        img = data['img']
        if img is None:
            img = np.zeros((480, 640, 3), np.uint8)

        for result in data['results']:
            xyxy = result['xyxy']
            cls = result['cls']
            x1y1 = xyxy[:2].astype(int)
            x2y2 = xyxy[2:].astype(int)
            cv2.rectangle(img, tuple(x1y1), tuple(x2y2), colors[cls], 2)

        data['show_img'] = img


def close_port(ip, port):
    import subprocess
    try:
        result = subprocess.run(
            f'''for /f "tokens=5" %a in ('netstat -ano ^| findstr {ip}:{port}') do taskkill /F /PID %a''',
            shell=True, capture_output=True, text=True)
        print(result.stdout)
    except Exception as e:
        print(f"Error closing port: {e}")


def sock(data):
    import socket

    while data['play']:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        while True:
            try:
                server_socket.bind((data['config']['ipv4_connect_to_CHT'], data['config']['port_connect_to_PLC']))
                break
            except OSError as e:
                print(f"Binding failed: {e}")
                close_port(data['config']['ipv4_connect_to_CHT'], data['config']['port_connect_to_PLC'])
                time.sleep(1)

        server_socket.listen(2)
        data['socket status'] = "Server Waiting for connection..."
        conn, address = server_socket.accept()
        data['socket status'] = f"Connection from: {address}"

        try:
            while True:
                socket_data = conn.recv(1024)
                if not socket_data:
                    break

                qr = data['count']['0 qr']['count']
                mark = data['count']['1 mark']['count']

                if qr == mark:
                    result = qr
                    data['socket_rs_output'] = f'{qr}'
                else:
                    result = 100
                    data['socket_rs_output'] = "NG"

                data['socket_qr_output'] = qr
                data['socket_mk_output'] = mark
                conn.send(result.to_bytes(2, byteorder='little'))

                now = datetime.now()
                json_update(f'history/{now.strftime("%y%m%d")}.json', {
                    f'{now.strftime("%H%M%S")}': {
                        'qr': qr,
                        'mark': mark,
                        'result': data['socket_rs_output'],
                    }
                })

        finally:
            conn.close()
            server_socket.close()
            data['socket status'] = "Connection closed"


def show(data):
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
    rect.center = (window_size[0] // 2, window_size[1] // 2)
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
    from app import run_server
    import hexss
    from hexss.threading import Multithread

    config = json_load('config.json',
                       {
                           'ipv4_connect_to_CHT': hexss.get_ipv4(),
                           "port_connect_to_CHT": 5555,
                           "ipv4_connect_to_PLC": hexss.get_ipv4(),
                           "port_connect_to_PLC": 9000,
                           "url_image": 'http://192.168.123.122:2000/image?source=video_capture&id=0'
                       }, True)

    data = {
        'config': config,
        'play': True,
        'socket status': '-',
        'socket_qr_output': '-',
        'socket_mk_output': '-',
        'socket_rs_output': '-',
        'img': None,
        'show_img': None,
        'results': [],
        'count': None
    }
    m = Multithread()
    m.add_func(show, args=(data,))
    m.add_func(predict, args=(data,))
    m.add_func(capture, args=(data,))
    m.add_func(sock, args=(data,), join=False)
    m.add_func(run_server, args=(data,), join=False)

    m.start()
    try:
        while data['play']:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        data['play'] = False
        m.join()
