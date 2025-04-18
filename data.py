# Manages the .ugit directory. This code will actually touch the disk.

import os

GIT_DIR = ".ugit"


def init():
    os.makedirs(GIT_DIR)

def hash_object(data):
    oid = hashlib.sha1(data).hexdigest()
    with open(f'{GIT_DIR}/object/{oid}', 'wb') as out:
        out.write(data)
    return oid

def get_object(oid):
    with open(f'{GIT_DIR}/object/{oid}', 'rb') as f:
        return f.read()