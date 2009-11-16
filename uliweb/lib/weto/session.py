#########################################################################
# session module written by limodou(limodou@gmail.com) at 2009/08/25
# this module is inspired by beaker package
#
# storage class will ensure the sync when load and save a session from 
# and to the storage.
#########################################################################
import os
import random
import time
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
    
class SessionException(Exception):pass
class SessionKeyException(Exception):pass

getpid = hasattr(os, 'getpid') and os.getpid or (lambda : '')

def _get_id():
    return md5(
                md5("%f%s%f%s" % (time.time(), id({}), random.random(),
                                  getpid())).hexdigest(), 
            ).hexdigest()

class SessionCookie(object):
    default_expiry_time = None #if None will use session expiry time
    default_domain = ''
    default_secure = False
    default_path = '/'
    default_cookie_id = 'session_cookie_id'
    
    def __init__(self, session):
        self.session = session
        self.domain = self.default_domain
        self.path = self.default_path
        self.secure = self.default_secure
        self.expiry_time = None
        self.cookie_id = self.default_cookie_id
        
    def save(self):
        self.expiry_time =  self.expiry_time or self.default_expiry_time or self.session.expiry_time
        
class Session(dict):
    default_expiry_time = 3600*24*365
    default_storage_type = 'file'
    default_options = {'table_name':'uliweb_session', 'data_dir':'./sessions',
        'file_dir':'./sessions/session_files',
        'lock_dir':'./sessions/session_files_lock'}
    
    def __init__(self, key=None, storage_type=None, options=None, expiry_time=None):
        dict.__init__(self)
        self._old_value = {}
        self._storage_type = storage_type or self.default_storage_type
        self._options = self.default_options
        if options:
            self._options.update(options.copy())
        self._storage_cls = self.__get_storage()
        self._storage = None
        self._accessed_time = None
        self.expiry_time = expiry_time or self.default_expiry_time
        self.key = key
        self.deleted = False
        self.cookie = SessionCookie(self)
        
        self.load(self.key)
        
    def __get_storage(self):
        modname = 'weto.backends.%s_storage' % self._storage_type
        mod = __import__(modname, {}, {}, [''])
        _class = getattr(mod, 'Storage', None)
        return _class
    
    def _set_remember(self, v):
        self['_session_remember_'] = v
        
    def _get_remember(self):
        return self.get('_session_remember_', True)
    
    remember = property(_get_remember, _set_remember)
    
    @property
    def storage(self):
        if not self._storage:
            self._storage = self._storage_cls(self._options)
        return self._storage
    
    def load(self, key=None):
        self.deleted = False
        self.clear()
        
        self.key = key
        if not self.key:
            return
        
        if not self.storage.read_ready(key):
            return
            
        lock = self.storage.get_lock(key)
        try:
            self.storage.acquire_read_lock(lock)
            ret = self.storage.load(key)
            if ret:
                stored_time, expiry_time, value = ret
                if self._is_not_expiry(stored_time, expiry_time):
                    self.update(value)
        except:
            self.storage.release_read_lock(lock, False)
        else:
            self.storage.release_read_lock(lock, True)
        self._old_value = self.copy()
            
    def _is_modified(self):
        return self._old_value != dict(self)
    
    def _is_not_expiry(self, accessed_time, expiry_time):
        return time.time() < accessed_time + expiry_time
        
    def save(self):
        if not self.deleted and (bool(self) or (not bool(self) and self._is_modified())):
            self.key = self.key or _get_id()
            now = time.time()

            lock = self.storage.get_lock(self.key)
            try:
                self.storage.acquire_write_lock(lock)
                self.storage.save(self.key, now, self.expiry_time, dict(self), self._is_modified())
                self.cookie.save()
            except:
                self.storage.release_write_lock(lock, False)
                raise
            else:
                self.storage.release_write_lock(lock, True)
                return True
        else:
            return False
        
    def delete(self):
        if self.key:
            lock = self.storage.get_lock(self.key)
            try:
                self.storage.acquire_write_lock(lock)
                self.storage.delete(self.key)
                self.clear()
                self._old_value = self.copy()
            except:
                self.storage.release_write_lock(lock, False)
                raise
            else:
                self.storage.release_write_lock(lock, True)
                self.storage.delete_lock(lock)
                
        self.deleted = True
         
    def _check(f):
        def _func(self, *args, **kw):
            try:
                if self.deleted:
                    raise SessionException, "The session object has been deleted!"
                return f(self, *args, **kw)
            finally:
                self._accessed_time = time.time()
        return _func
    
    clear = _check(dict.clear)
    __getitem__ = _check(dict.__getitem__)
    __setitem__ = _check(dict.__setitem__)
    __delitem__ = _check(dict.__delitem__)
    pop = _check(dict.pop)
    popitem = _check(dict.popitem)
    setdefault = _check(dict.setdefault)
    update = _check(dict.update)
    
    