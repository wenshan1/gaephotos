#########################################################################
# cache module written by limodou(limodou@gmail.com) at 2009/11/03
#
# storage class will ensure the sync when load and save a session from 
# and to the storage.
#########################################################################
import time

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

def _get_key(key):
    if isinstance(key, unicode):
        key = key.encode('ascii', 'backslashreplace')
    
    return md5(key).hexdigest()

def wrap_func(des, src):
    des.__name__ = src.__name__
    des.func_globals.update(src.func_globals)
    des.__doc__ = src.__doc__
    des.__module__ = src.__module__
    des.__dict__.update(src.__dict__)
    return des

class CacheKeyException(Exception):pass

class Cache(object):
    default_expiry_time = 3600*24*365
    default_storage_type = 'file'
    default_options = {'table_name':'uliweb_cache', 'data_dir':'./caches',
        'file_dir':'./caches/cache_files',
        'lock_dir':'./caches/cache_files_lock'}
    
    def __init__(self, storage_type=None, options=None, expiry_time=None):
        self._modules = {}
        self._storage_type = storage_type or self.default_storage_type
        self._options = self.default_options
        if options:
            self._options.update(options.copy())
        self._storage_cls = self.__get_storage()
        self._storage = None
        self.expiry_time = expiry_time or self.default_expiry_time
     
    def __get_storage(self):
        modname = 'weto.backends.%s_storage' % self._storage_type
        if modname in self._modules:
            return self._modules[modname]
        else:
            mod = __import__(modname, {}, {}, [''])
            _class = getattr(mod, 'Storage', None)
            self._modules[modname] = _class
        return _class
    
    @property
    def storage(self):
        if not self._storage:
            self._storage = self._storage_cls(self._options)
        return self._storage
    
    def get(self, k=None, default=None):
        key = _get_key(k)
        if not self.storage.read_ready(key):
            if default is None:
                raise CacheKeyException, "Cache key [%s] not found" % k
            return default
            
        lock = self.storage.get_lock(key)
        try:
            self.storage.acquire_read_lock(lock)
            ret = self.storage.load(key)
            if ret:
                stored_time, expiry_time, value = ret
                if self._is_not_expiry(stored_time, expiry_time):
                    return value
        except:
            self.storage.release_read_lock(lock, False)
        else:
            self.storage.release_read_lock(lock, True)
        if default is None:
            raise CacheKeyException, "Cache key [%s] not found" % k
        return default
            
    def _is_not_expiry(self, accessed_time, expiry_time):
        return time.time() < accessed_time + expiry_time
        
    def put(self, key, value=None, expire=None):
        if value is None:
            return True
        key = _get_key(key)
        now = time.time()

        lock = self.storage.get_lock(key)
        try:
            self.storage.acquire_write_lock(lock)
            self.storage.save(key, now, expire or self.expiry_time, value, True)
        except:
            self.storage.release_write_lock(lock, False)
            raise
        else:
            self.storage.release_write_lock(lock, True)
            return True
        
    def delete(self, key):
        key = _get_key(key)
        lock = self.storage.get_lock(key)
        try:
            self.storage.acquire_write_lock(lock)
            self.storage.delete(key)
        except:
            self.storage.release_write_lock(lock, False)
            raise
        else:
            self.storage.release_write_lock(lock, True)
            self.storage.delete_lock(lock)
             
    def __getitem__(self, key):
        return self.get(key)
    
    def __setitem__(self, key, value):
        return self.put(key, value)
    
    def __delitem__(self, key):
        self.delete(key)
        
    def setdefault(self, key, defaultvalue, expire=None):
        try:
            v = self.get(key)
            return v
        except CacheKeyException:
            self.put(key, defaultvalue, expire=expire)
            return defaultvalue
        
    def cache(self, k=None, expire=None):
        def _f(func):
            def f(*args, **kwargs):
                if not k:
                    r = repr(args) + repr(sorted(kwargs.items()))
                    key = func.__module__ + '.' + func.__name__ + r
                else:
                    key = k
                try:
                    ret = self.get(key)
                    return ret
                except CacheKeyException:
                    ret = func(*args, **kwargs)
                    self.put(key, ret, expire=expire)
                    return ret
            
            wrap_func(f, func)
            return f
        return _f
    
    
