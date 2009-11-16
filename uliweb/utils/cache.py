import uliweb
from weto.cache import Cache as CacheCls, CacheKeyException
from uliweb import Response
from uliweb.core.SimpleFrame import ResponseProxy
from uliweb.utils.common import wraps

def get_cache(cache_setting_name='CACHE', cache_storage_setting_name='CACHE_STORAGE'):
    cache = Cache(uliweb.settings.get_var('%s/type' % cache_setting_name), 
        options=uliweb.settings.get_var('%s' % cache_storage_setting_name),
        expiry_time=uliweb.settings.get_var('%s/expiretime' % cache_setting_name))
    return cache

class Cache(CacheCls):
    def page(self, k=None, expire=None):
        def _f(func):
            @wraps(func)
            def f(*args, **kwargs):
                from uliweb import request
                if not k:
                    key = request.url
                else:
                    key = k
                try:
                    ret = self.get(key)
                    return ret
                except CacheKeyException:
                    ret = func(*args, **kwargs)
                    if isinstance(ret, (Response, ResponseProxy)):
                        ret = ret.data
                    self.put(key, ret, expire=expire)
                    return ret
            
            return f
        return _f


