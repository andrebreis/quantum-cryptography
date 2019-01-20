import ecdsa
import hashlib
import os
import time


def generate_private_key():
    return ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)


def generate_public_key(private_key):
    return private_key.get_verifying_key()


def verify(public_key, msg):
    if type(msg['msg']) == str:
        msg['msg'] = msg['msg'].encode('UTF-8')
    public_key.verify(msg['signature'], msg['msg'], hashfunc=hashlib.sha256)


def sign(private_key, msg):
    if type(msg) == str:
        msg = msg.encode('UTF-8')
    return {
        'msg': msg,
        'signature': private_key.sign(msg, hashfunc=hashlib.sha256)
    }


def publish_public_key(party, private_key):
    """
    :param party:
    :param private_key:
    :return:
    """
    public_key = generate_public_key(private_key)
    f = open(party + '_pkey.pem', 'wb')
    f.write(public_key.to_pem())
    f.close()
    return public_key


def get_public_key(party):
    """
    :param party:
    :return:
    """
    filename = party + '_pkey.pem'
    while not os.path.isfile(filename) or not os.stat(filename).st_size > 0:
        time.sleep(1)
    f = open(filename, 'rb')
    pkey = ecdsa.VerifyingKey.from_pem(f.read())
    f.close()
    return pkey
