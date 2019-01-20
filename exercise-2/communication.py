import pickle
import socket


def send_message(sender, receiver_name, msg):
    # print(sender, receiver_name, msg)
    socket_info = sender._appNet.getStateFor(sender.name)['hostDict'][receiver_name]
    s = socket.socket()
    while True:
        try:
            s.connect((socket_info.hostname, socket_info.port))
            break
        except Exception as e:
            continue
    s.send(pickle.dumps(len(msg)))
    ack = s.recv(32)
    bytes_sent = 0
    while bytes_sent < len(msg):
        bytes_sent += s.send(msg[bytes_sent:])
    ack = s.recv(32)
    s.close()


def receive_message(receiver):
    socket_info = receiver._appNet.getStateFor(receiver.name)['hostDict'][receiver.name]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((socket_info.hostname, socket_info.port))
    s.listen(1)
    c, addr = s.accept()
    len_msg = pickle.loads(c.recv(256)) #.decode('utf-8')
    c.send('ACK'.encode('UTF-8'))
    msg = b''
    while len(msg) < len_msg:
        msg += c.recv(4096)
    c.send('ACK'.encode('UTF-8'))
    c.close()
    s.close()
    return msg
