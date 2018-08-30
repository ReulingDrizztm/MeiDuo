import pickle
import base64


def dumps(cart_dict):
    cart_byte = pickle.dumps(cart_dict)
    cart_64 = base64.b64encode(cart_byte)
    cart_str = cart_64.decode()

    return cart_str


def loads(cart_str):
    cart_64 = cart_str.encode()
    cart_byte = base64.b64decode(cart_64)
    cart_dict = pickle.loads(cart_byte)

    return cart_dict
