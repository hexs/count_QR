def capture(data):
    from hexss.image import get_image
    import time

    url = 'http://192.168.123.122:2000/image?source=video_capture&id=0'
    while data['play']:
        img = get_image(url)
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


def sock(data):
    import socket

    while data['play']:
        server_socket = socket.socket()
        server_socket.bind(('192.168.3.1', 9000))

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

            qr = data['count'].get('0 qr', {}).get('count', 0)
            mark = data['count'].get('1 mark', {}).get('count', 0)

            message = f'{qr:02}' if qr == mark else 'ng'
            data['socket output'] = message
            print(message)
            print()
            conn.send(message.encode())
        conn.close()


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

    res_text_box = UITextBox("-", Rect(640, 0, 220, 480), manager)
    socket_status_label = UITextBox('-', Rect(0, 480, 640, 30), manager)
    socket_output_label = UITextBox('-', Rect(640, 480, 220, 30), manager)

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
            socket_output_label.set_text(data['socket output'])
            res_text_box.set_text(json.dumps(data['count'], indent=4))
            display.blit(numpy_to_pygame_surface(img), (0, 0))

        manager.draw_ui(display)
        pygame.display.update()

    pygame.quit()


if __name__ == '__main__':
    from hexss.multiprocessing import Multicore
    import hexss

    m = Multicore()
    m.set_data({
        'play': True,
        'socket status': '-',
        'socket output': '-',
        'img': None,
        'results': [],
        'count': None
    })
    m.add_func(show)
    m.add_func(predict)
    m.add_func(capture)
    m.add_func(sock, join=False)

    m.start()
    m.join()

    hexss.kill()
