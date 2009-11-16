import os
from weto.backends import file_storage
import cPickle
from base import verify_path

class Storage(file_storage.Storage):
    def __init__(self, options):
        file_storage.Storage.__init__(self, options)
        mod = options.get('dbm_module', 'anydbm')
        self.dbm_module = __import__(mod, {}, {}, [''])

    def load(self, key):
        if key:
            session_file = self.get_session_file(key)
            if os.path.exists(session_file):
                f = self.dbm_module.open(session_file, 'r')
                try:
                    try:
                        v = cPickle.loads(f[key])
                        return v
                    except (IOError, OSError, EOFError, cPickle.PickleError, ValueError):
                        pass
                finally:
                    f.close()
    
    def save(self, key, stored_time, expiry_time, value, modified):
        if key:
            session_file = self.get_session_file(key)
            verify_path(session_file)
            f = self.dbm_module.open(session_file, 'c')
            try:
                try:
                    f[key] = cPickle.dumps((stored_time, expiry_time, value))
                except (IOError, OSError, EOFError, cPickle.PickleError, ValueError):
                    pass
            finally:
                f.close()
    
