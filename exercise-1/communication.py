import socket


def send_message(sender, receiver_name, msg):
    socket_info = sender._appNet.getStateFor(sender.name)['hostDict'][receiver_name]
    s = socket.socket()
    # sent = 0
    while True:
        try:
            s.connect((socket_info.hostname, socket_info.port))
            s.send(msg)
            # if sent == len(msg):
            break
        except ConnectionRefusedError:
            continue
    s.close()


def receive_message(receiver):
    socket_info = receiver._appNet.getStateFor(receiver.name)['hostDict'][receiver.name]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((socket_info.hostname, socket_info.port))
    s.listen(5)
    c, addr = s.accept()
    msg = c.recv(1024) #.decode('utf-8')
    c.close()
    s.close()
    return msg
