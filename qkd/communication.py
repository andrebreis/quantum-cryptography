import pickle
import authentication as auth
import json
import socket


def bitlist_to_bytes(bitlist):
    bytelist = b''
    padded = False
    for i in range(0, len(bitlist), 8):
        byte = 0
        for j in range(0, 8):
            if i+j == len(bitlist):
                byte += pow(2, 7-j)
                padded = True
                break
            byte += bitlist[i+j]*pow(2, 7-j)
        bytelist += bytes([byte])
    if not padded:
        bytelist += bytes([pow(2, 7)])
    return bytelist


def bytes_to_bitlist(bytelist):
    bitlist = []
    for byte in bytelist:
        for i in range(0, 8):
            if (byte & (1 << 7-i)) > 0:
                bitlist.append(1)
            else:
                bitlist.append(0)
    for i in reversed(range(0, len(bitlist))):
        if bitlist[i] == 1:
            del bitlist[i]
            return bitlist
        else:
            del bitlist[i]


def _send_message(sender, receiver_name, msg):
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


def _receive_message(receiver):
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


def dict_to_binary(the_dict):
    return bytes(list(pickle.dumps(the_dict)))


def binary_to_dict(binary):
    return pickle.loads(binary)


def send_message(sender, receiver, sk, msg):
    _send_message(sender, receiver, dict_to_binary(auth.sign(sk, str(msg))))


def send_binary_list(sender, receiver, sk, list):
    _send_message(sender, receiver, dict_to_binary(auth.sign(sk, bitlist_to_bytes(list))))


def receive_message(receiver, pk):
    message_dict = binary_to_dict(_receive_message(receiver))
    auth.verify(pk, message_dict)
    return message_dict['msg'].decode('UTF-8')


def receive_list(receiver, pk):
    return json.loads(receive_message(receiver, pk))


def receive_binary_list(receiver, pk):
    message_dict = binary_to_dict(_receive_message(receiver))
    auth.verify(pk, message_dict)
    return bytes_to_bitlist(message_dict['msg'])
