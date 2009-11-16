import os
import cPickle
from base import BaseStorage, verify_path, encoded_path
import weto.lockfile as lockfile

class Storage(BaseStorage):
    def __init__(self, options):
        self.data_dir = options.get('data_dir', './sessions')
        self.file_dir = options.get('file_dir') or os.path.join(self.data_dir, 'session_files')
        self.lock_dir = options.get('lock_dir') or os.path.join(self.data_dir, 'session_files_lock')
        
    def get_session_file(self, key):
        return encoded_path(self.file_dir, key, '.ses')
    
    def get_lock(self, key):
        lfile = encoded_path(self.lock_dir, key, '.lock')
        return lockfile.LockFile(lfile)
    
    def read_ready(self, key):
        if key:
            session_file = self.get_session_file(key)
            return os.path.exists(session_file)
        
    def acquire_read_lock(self, lock):
        lock.lock()
        
    def release_read_lock(self, lock, success):
        lock.close()
        
    def acquire_write_lock(self, lock):
        lock.lock(lockfile.LOCK_EX)
        
    def release_write_lock(self, lock, success):
        lock.close()
      
    def load(self, key):
        if key:
            session_file = self.get_session_file(key)
            if os.path.exists(session_file):
                f = open(session_file, 'rb')
                try:
                    try:
                        v = cPickle.load(f)
                        return v
                    except (IOError, OSError, EOFError, cPickle.PickleError, ValueError):
                        pass
                finally:
                    f.close()
    
    def save(self, key, stored_time, expiry_time, value, modified):
        if key:
            session_file = self.get_session_file(key)
            verify_path(session_file)
            f = open(session_file, 'wb')
            try:
                try:
                    cPickle.dump((stored_time, expiry_time, value), f)
                except (IOError, OSError, EOFError, cPickle.PickleError, ValueError):
                    pass
            finally:
                f.close()
    
    def delete(self, key):
        if key:
            session_file = self.get_session_file(key)
            if os.path.exists(session_file):
                os.unlink(session_file)
                
    def delete_lock(self, lock):
        if lock:
            lock.delete()
    