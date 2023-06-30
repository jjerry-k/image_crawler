import os

ROOT = "/Data/Crawling"
os.makedirs(ROOT, exist_ok=True)

import hashlib

def convert_hash(file):
    if not isinstance(file, (bytes)):
        with open(file, 'rb') as f:
            file = f.read()
    md5 = hashlib.md5()
    md5.update(file)
    return md5.hexdigest()