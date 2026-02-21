import hashlib

def file_hash(content: bytes):
    return hashlib.md5(content).hexdigest()
