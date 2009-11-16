__all__ = ['verify_path', 'encoded_path', 'BaseStorage', 'StorageError']

import os

try:
    from hashlib import sha1
except ImportError:
    from sha import sha as sha1
    
class StorageError(Exception):
    pass

def verify_path(path):
    dir = os.path.dirname(path)
    if dir and not os.path.exists(dir):
        os.makedirs(dir)
    
def encoded_path(root, key, extension = ".enc", depth = 2):
    ident = sha1(key).hexdigest()
    
    tokens = []
    for d in range(0, depth):
        tokens.append(ident[d])
    
    dir = os.path.join(root, *tokens)
    
    return os.path.join(dir, ident + extension)

class BaseStorage(object):
    def __init__(self, options):
        self.options = options
        
    def load(self, key):
        raise NotImplementedError()
    
    def save(self, key, store_time, expiry_time, value, modified):
        raise NotImplementedError()
    
    def delete(self, key):
        raise NotImplementedError()
    
    def read_ready(self, key):
        raise NotImplementedError()
    
    def get_lock(self, key):
        raise NotImplementedError()
    
    def acquire_read_lock(self, lock):
        raise NotImplementedError()
        
    def release_read_lock(self, lock, success):
        raise NotImplementedError()
        
    def acquire_write_lock(self, lock):
        raise NotImplementedError()
        
    def release_write_lock(self, lock, success):
        raise NotImplementedError()
    
    def delete_lock(self, lock):
        raise NotImplementedError()
    