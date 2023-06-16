import base64

from cryptography.fernet import Fernet


def encrypt(key, msg):
    key = (key * 32)[:32]
    key = base64.urlsafe_b64encode(key.encode())
    f = Fernet(key)
    return f.encrypt(msg.encode()).decode()


def decrypt(key, msg):
    key = (key * 32)[:32]
    key = base64.urlsafe_b64encode(key.encode())
    f = Fernet(key)
    return f.decrypt(msg.encode()).decode()
