####################################################################
# Author: Limodou@gmail.com
# License: BSD
####################################################################

import os, sys
import cgi
from werkzeug import Request as OriginalRequest, Response as OriginalResponse
from werkzeug import ClosingIterator, Local, LocalManager, BaseResponse
from werkzeug.exceptions import HTTPException, NotFound, InternalServerError

import template
from storage import Storage
import dispatch
from uliweb.utils.common import pkg, log, sort_list, import_func, import_mod_func, myimport, wrap_func
from uliweb.utils.pyini import Ini
import uliweb as conf
from rules import Mapping, add_rule

try:
    import json as JSON
except:
    import simplejson as JSON

try:
    set
except:
    from sets import Set as set

conf.local = local = Local()
local_manager = LocalManager([local])

conf.url_map = Mapping()
__app_dirs = {}
_use_urls = False

class Request(OriginalRequest):
    GET = OriginalRequest.args
    POST = OriginalRequest.form
    params = OriginalRequest.values
    FILES = OriginalRequest.files
    
class Response(OriginalResponse):
    def write(self, value):
        self.stream.write(value)
    
class RequestProxy(object):
    def instance(self):
        return conf.local.request
        
    def __getattr__(self, name):
        return getattr(conf.local.request, name)
    
    def __setattr__(self, name, value):
        setattr(conf.local.request, name, value)
        
    def __str__(self):
        return str(conf.local.request)
    
    def __repr__(self):
        return repr(conf.local.request)
            
class ResponseProxy(object):
    def instance(self):
        return conf.local.response
        
    def __getattr__(self, name):
        return getattr(conf.local.response, name)
    
    def __setattr__(self, name, value):
        setattr(conf.local.response, name, value)

    def __str__(self):
        return str(conf.local.response)
    
    def __repr__(self):
        return repr(conf.local.response)
    
class HTTPError(Exception):
    def __init__(self, errorpage=None, **kwargs):
        self.errorpage = errorpage or conf.settings.GLOBAL.ERROR_PAGE
        self.errors = kwargs

    def __str__(self):
        return repr(self.errors)
   
def redirect(location, code=302):
    response = Response(
        '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
        '<title>Redirecting...</title>\n'
        '<h1>Redirecting...</h1>\n'
        '<p>You should be redirected automatically to target URL: '
        '<a href="%s">%s</a>.  If not click the link.' %
        (cgi.escape(location), cgi.escape(location)), status=code, content_type='text/html')
    response.headers['Location'] = location
    return response

def error(message='', errorpage=None, request=None, appname=None, **kwargs):
    kwargs.setdefault('message', message)
    if request:
        kwargs.setdefault('link', request.url)
    raise HTTPError(errorpage, **kwargs)

def json(data):
    return Response(JSON.dumps(data), content_type='application/json; charset=utf-8')

class ReservedKeyError(Exception):pass

reserved_keys = ['settings', 'redirect', 'application', 'request', 'response', 'error']

def _get_rule(f):
    import inspect
    args = inspect.getargspec(f)[0]
    if args :
        args = ['<%s>' % x for x in args]
    if f.__name__ in reserved_keys:
        raise ReservedKeyError, 'The name "%s" is a reversed key, so please change another one' % f.__name__
    m = f.__module__.split('.')
    s = []
    for i in m:
        if not i.startswith('views'):
            s.append(i)
    appname = '.'.join(s)
    rule = '/' + '/'.join(['/'.join(s), f.__name__] + args)
    return appname, rule
    
def expose(rule=None, **kw):
    """
    add a url assigned to the function to url_map, if rule is None, then
    the url will be function name, for example:
        
        @expose
        def index(req):
            
        will be url_map.add('index', index)
    """
    def fix_url(module, url):
        m = module.split('.')
        s = []
        for i in m:
            if not i.startswith('views'):
                s.append(i)
        appname = '.'.join(s)
        
        if 'URL' in conf.settings and appname in conf.settings.URL:
            suffix = conf.settings.URL[appname]
            url = url.lstrip('/')
            return os.path.join(suffix, url).replace('\\', '/')
        else:
            return url
        
    static = kw.get('static', None)
    if callable(rule):
        if conf.use_urls:
            return rule
        f = rule
        appname, rule = _get_rule(f)
        kw['endpoint'] = f.__module__ + '.' + f.__name__
        rule = fix_url(appname, rule)
        conf.urls.append((rule, kw))
        if static:
            conf.static_views.append(kw['endpoint'])
        if 'static' in kw:
            kw.pop('static')
        add_rule(conf.url_map, rule, **kw)
        return f
        
    def decorate(f, rule=rule):
        if conf.use_urls:
            return f
        if callable(f):
            appname, x = _get_rule(f)
        if not rule:
            rule = x
        if callable(f):
            f_name = f.__name__
            endpoint = f.__module__ + '.' + f.__name__
            module = appname
        else:
            f_name = f.split('.')[-1]
            endpoint = f
            module = f
            
        if f_name in reserved_keys:
            raise ReservedKeyError, 'The name "%s" is a reversed key, so please change another one' % f_name
        kw['endpoint'] = endpoint
        rule = fix_url(module, rule)
        conf.urls.append((rule, kw))
        if static:
            conf.static_views.append(kw['endpoint'])
        if 'static' in kw:
            kw.pop('static')
        add_rule(conf.url_map, rule, **kw)
        return f
    return decorate

def pre_view(topic, *args1, **kwargs1):
    methods = kwargs1.pop('methods', None)
    signal = kwargs1.pop('signal', None)
    def _f(f):
        def _f2(*args, **kwargs):
            m = methods or []
            m = [x.upper() for x in m]
            if not m or (m and conf.local.request.method in m):
                ret = dispatch.get(conf.local.application, topic, signal=signal, *args1, **kwargs1)
                if ret:
                    return ret
            return f(*args, **kwargs)
        return wrap_func(_f2, f)
    return _f

def post_view(topic, *args1, **kwargs1):
    methods = kwargs1.pop('methods', None)
    signal = kwargs1.pop('signal', None)
    def _f(f):
        def _f2(*args, **kwargs):
            m = methods or []
            m = [x.upper() for x in m]
            ret = f(*args, **kwargs)
            ret1 = None
            if not m or (m and conf.local.request.method in m):
                ret1 = dispatch.get(conf.local.application, topic, signal=signal, *args1, **kwargs1)
            return ret or ret1
        return wrap_func(_f2, f)
    return _f
    
def POST(rule, **kw):
    kw['methods'] = ['POST']
    return expose(rule, **kw)

def GET(rule, **kw):
    kw['methods'] = ['GET']
    return expose(rule, **kw)

def url_for(endpoint, **values):
    if callable(endpoint):
        endpoint = endpoint.__module__ + '.' + endpoint.__name__
    _external = values.pop('_external', False)
    return conf.local.url_adapter.build(endpoint, values, force_external=_external)

def get_app_dir(app):
    """
    Get an app's directory
    """
    path = __app_dirs.get(app)
    if path is not None:
        return path
    else:
        p = app.split('.')
        try:
            path = pkg.resource_filename(p[0], '')
        except ImportError, e:
            log.exception(e)
            path = ''
        if len(p) > 1:
            path = os.path.join(path, *p[1:])
        
        __app_dirs[app] = path
        return path

def get_apps(apps_dir, include_apps=None):
    include_apps = include_apps or []
    inifile = os.path.join(apps_dir, 'settings.ini')
    apps = []
    if os.path.exists(inifile):
        x = Ini(inifile)
        apps = x.GLOBAL.get('INSTALLED_APPS', [])
    if not apps and os.path.exists(apps_dir):
        for p in os.listdir(apps_dir):
            if os.path.isdir(os.path.join(apps_dir, p)) and p not in ['.svn', 'CVS'] and not p.startswith('.') and not p.startswith('_'):
                apps.append(p)
    
    apps.extend(include_apps)
    #process dependencies
    s = apps[:]
    visited = set()
    while s:
        p = s.pop()
        if p in visited:
            continue
        else:
            configfile = os.path.join(get_app_dir(p), 'config.ini')
            
            if os.path.exists(configfile):
                x = Ini(configfile)
                if 'DEFAULT' in x:
                    for i in x.DEFAULT.get('REQUIRED_APPS', []):
                        if i not in apps:
                            apps.append(i)
                        if i not in visited:
                            s.append(i)
            visited.add(p)

    return apps

class Loader(object):
    def __init__(self, tmpfilename, vars, env, dirs, notest=False):
        self.tmpfilename = tmpfilename
        self.dirs = dirs
        self.vars = vars
        self.env = env
        self.notest = notest
        
    def get_source(self, exc_type, exc_value, exc_info, tb):
        f, t, e = template.render_file(self.tmpfilename, self.vars, self.env, self.dirs)
        if exc_type is SyntaxError:
            import re
            r = re.search(r'line (\d+)', str(exc_value))
            lineno = int(r.group(1))
        else:
            lineno = tb.tb_frame.f_lineno
        return self.tmpfilename, lineno, t 
    
    def test(self, filename):
        if self.notest:
            return True
        return filename.endswith('.html')

class DummyObject(int):
    def __str__(self):
        return ''
    
    def __unicode__(self):
        return u''
    
    def __getattr__(self, name):
        return DummyObject()
    
    def __setattr__(self, name, value):
        pass
    
    def __iter__(self):
        return self

    def next(self):
        raise StopIteration()
       
class Dispatcher(object):
    installed = False
    def __init__(self, apps_dir='apps', use_urls=None, include_apps=None, start=True):
        self.debug = False
        self.use_urls = conf.use_urls = use_urls
        self.include_apps = include_apps or []
        if not Dispatcher.installed:
            self.init(apps_dir)
            dispatch.call(self, 'startup_installed')
            
        if start:
            dispatch.call(self, 'startup')
    
    def init(self, apps_dir):
        conf.apps_dir = apps_dir
        Dispatcher.apps_dir = apps_dir
        Dispatcher.apps = get_apps(self.apps_dir, self.include_apps)
        #add urls.py judgement
        flag = True
        if self.use_urls is None or self.use_urls is True:
            try:
                import urls
                from uliweb.core import rules
                conf.url_map = urls.url_map
                conf.static_views = rules.static_views
                flag = False
            except ImportError:
                pass
        Dispatcher.modules = self.collect_modules(flag)
        self.install_settings(self.modules['settings'])
        Dispatcher.settings = conf.settings
        Dispatcher.env = self._prepare_env()
        Dispatcher.template_dirs = self.get_template_dirs()
        self.install_apps()
        Dispatcher.url_map = conf.url_map
        if flag:
            self.install_views(self.modules['views'])
            Dispatcher.url_infos = conf.urls
        else:
            Dispatcher.url_infos = []
#        Dispatcher.templateplugins_dirs = self.get_templateplugins_dirs()
        
        #process dispatch hooks
        self.dispatch_hooks()
        
        self.debug = conf.settings.GLOBAL.get('DEBUG', False)
        dispatch.call(self, 'prepare_default_env', Dispatcher.env)
        Dispatcher.default_template = pkg.resource_filename('uliweb.core', 'default.html')
        
        Dispatcher.installed = True
        
    def _prepare_env(self):
        env = Storage({})
        env['url_for'] = url_for
        env['redirect'] = redirect
        env['error'] = error
        env['application'] = self
        env['settings'] = conf.settings
        env['json'] = json
        return env
    
    def get_file(self, filename, dir='static'):
        """
        get_file will search from apps directory
        """
        if os.path.exists(filename):
            return filename
        if conf.request:
            dirs = [conf.request.appname] + self.apps
        else:
            dirs = self.apps
        fname = os.path.join(dir, filename)
        for d in dirs:
            path = pkg.resource_filename(d, fname)
            if os.path.exists(path):
                return path
        return None

    def template(self, filename, vars=None, env=None, dirs=None, request=None, default_template=None):
        vars = vars or {}
        dirs = dirs or self.template_dirs
        env = env or self.get_view_env()
        request = request or local.request
        if request:
            dirs = [os.path.join(get_app_dir(request.appname), 'templates')] + dirs
        
        d = dispatch.get(self, 'get_template_dirs', dirs, request)
        if d:
            dirs = d
        
        handlers = {}
        dispatch.call(self, 'get_template_tag_handlers', handlers)
        if self.debug:
            def _compile(code, filename, action):
                __loader__ = Loader(filename, vars, env, dirs, notest=True)
                return compile(code, filename, 'exec')
            
            dispatch.call(self, 'before_render_template', vars, env)
            fname, code, e = template.render_file(filename, vars, env, dirs, 
                default_template=default_template, handlers=handlers)
                
            #user can insert new local environment variables to e variable
            #and e will be a Context object
            dispatch.call(self, 'before_compile_template', fname, code, vars, e)
            out = template.Out()
            new_e = template._prepare_run(vars, e, out)

            if isinstance(code, (str, unicode)):
                code = _compile(code, fname, 'exec')
                defined = new_e['defined']
                names = code.co_names
                for name in names:
                    if not name in new_e:
                        if not defined(name):
                            if not name in __builtins__:
                                new_e[name] = DummyObject()

            __loader__ = Loader(fname, vars, env, dirs)
            exec code in new_e
            text = out.getvalue()
            output = dispatch.get(self, 'after_render_template', text, vars, e)
            return output or text
        else:
            dispatch.call(self, 'before_render_template', vars, env)
            fname, code, e = template.render_file(filename, vars, env, dirs, 
                default_template=default_template, handlers=handlers)
                
            dispatch.call(self, 'before_compile_template', vars, e)
            out = template.Out()
            new_e = template._prepare_run(vars, e, out)
            
            if isinstance(code, (str, unicode)):
                code = compile(code, fname, 'exec')
                names = code.co_names
                defined = new_e['defined']
                for name in names:
                    if not name in new_e:
                        if not defined(name):
                            if not name in __builtins__:
                                new_e[name] = DummyObject()
            exec code in new_e
            text = out.getvalue()
            output = dispatch.get(self, 'after_render_template', text, vars, e)
            return output or text
    
    def render(self, templatefile, vars, env=None, dirs=None, request=None, default_template=None):
        return Response(self.template(templatefile, vars, env, dirs, request, default_template=default_template), content_type='text/html')
    
    def _page_not_found(self, description=None, **kwargs):
        description = 'The requested URL "{{=url}}" was not found on the server.'
        text = """<h1>Page Not Found</h1>
    <p>%s</p>
    <h3>Current URL Mapping is</h3>
    <table border="1">
    <tr><th>URL</th><th>View Functions</th></tr>
    {{for url, methods, endpoint in urls:}}
    <tr><td>{{=url}} {{=methods}}</td><td>{{=endpoint}}</td></tr>
    {{pass}}
    </table>
    """ % description
        return Response(template.template(text, kwargs), status=404, content_type='text/html')
        
    def not_found(self, request, e):
        if self.debug:
            urls = []
            for r in self.url_map.iter_rules():
                if r.methods:
                    methods = ' '.join(list(r.methods))
                else:
                    methods = ''
                urls.append((r.rule, methods, r.endpoint))
            urls.sort()
            return self._page_not_found(url=request.path, urls=urls)
        tmp_file = template.get_templatefile('404'+conf.settings.GLOBAL.TEMPLATE_SUFFIX, self.template_dirs)
        if tmp_file:
            response = self.render(tmp_file, {'url':request.path})
            response.status = 404
        else:
            response = e
        return response
    
    def internal_error(self, request, e):
        tmp_file = template.get_templatefile('500'+conf.settings.GLOBAL.TEMPLATE_SUFFIX, self.template_dirs)
        if tmp_file:
            response = self.render(tmp_file, {'url':request.path})
            response.status = 500
        else:
            response = e
        return response
    
    def get_env(self, env=None):
        e = Storage(self.env.copy())
        if env:
            e.update(env)
        return e
    
    def prepare_request(self, request, endpoint):
        #binding some variable to request
        request.settings = conf.settings
        request.application = self
        
        #get handler
        if isinstance(endpoint, (str, unicode)):
            mod, handler = import_mod_func(endpoint)
        elif callable(endpoint):
            handler = endpoint
            mod = sys.modules[handler.__module__]
        
        request.appname = ''
        for p in self.apps:
            t = p + '.'
            if handler.__module__.startswith(t):
                request.appname = p
                break
        request.function = handler.__name__
        return mod, handler
    
    def call_view(self, mod, handler, request, response=None, **values):
        #get env
        env = self.get_view_env()
        
        #if there is __begin__ then invoke it, if __begin__ return None, it'll
        #continue running
        if hasattr(mod, '__begin__'):
            f = getattr(mod, '__begin__')
            result = self._call_function(f, request, response, env)
            if result is not None:
                return self.wrap_result(result, request, response, env)
        
        result = self.call_handler(handler, request, response, env, **values)

        result1 = None
        if hasattr(mod, '__end__'):
            f = getattr(mod, '__end__')
            result1, env = self._call_function(f, request, response, env)
            if result1 is not None:
                return self.wrap_result(result1, request, response, env)
        
        return result or result1
        
    def wrap_result(self, result, request, response, env):
#        #process ajax invoke, return a json response
#        if request.is_xhr and isinstance(result, dict):
#            result = Response(JSON.dumps(result), content_type='application/json')

        if isinstance(result, dict):
            result = Storage(result)
            if hasattr(response, 'template'):
                tmpfile = response.template
            else:
                tmpfile = request.function + conf.settings.GLOBAL.TEMPLATE_SUFFIX
            
            #if debug mode, then display a default_template
            if self.debug:
                d = ['default.html', self.default_template]
            else:
                d = None
            response = self.render(tmpfile, result, env=env, request=request, default_template=d)
        elif isinstance(result, (str, unicode)):
            response = Response(result, content_type='text/html')
        elif isinstance(result, (Response, BaseResponse)):
            response = result
        else:
            response = Response(str(result), content_type='text/html')
        return response
    
    def get_view_env(self):
        #prepare local env
        local_env = {}
        
        #process before view call
        dispatch.call(self, 'prepare_view_env', local_env, local.request)
        
        local_env['application'] = local.application
        local_env['request'] = conf.request
        local_env['response'] = conf.response
        local_env['url_for'] = url_for
        local_env['redirect'] = redirect
        local_env['error'] = error
        local_env['settings'] = conf.settings
        local_env['json'] = json
        
        return self.get_env(local_env)
       
    def _call_function(self, handler, request, response, env, **values):
        
        for k, v in env.iteritems():
            handler.func_globals[k] = v
        
        handler.func_globals['env'] = env
        
        result = handler(**values)
        if isinstance(result, ResponseProxy):
            result = local.response
        return result
    
    def call_handler(self, handler, request, response, env, **values):
        result = self._call_function(handler, request, response, env, **values)
        return self.wrap_result(result, request, response, env)
            
    def collect_modules(self, check_view=True):
        modules = {}
        views = set()
        settings = []
        set_ini = os.path.join(self.apps_dir, 'settings.ini')
        if os.path.exists(set_ini):
            settings.append(set_ini)
        
        def enum_views(views_path, appname, subfolder=None, pattern=None):
            for f in os.listdir(views_path):
                fname, ext = os.path.splitext(f)
                if os.path.isfile(os.path.join(views_path, f)) and ext in ['.py', '.pyc', '.pyo'] and fname!='__init__':
                    if pattern:
                        import fnmatch
                        if not fnmatch.fnmatch(f, pattern):
                            continue
                    if subfolder:
                        views.add('.'.join([appname, subfolder, fname]))
                    else:
                        views.add('.'.join([appname, fname]))

        for p in self.apps:
            path = get_app_dir(p)
            #deal with views
            if check_view:
                views_path = os.path.join(path, 'views')
                if os.path.exists(views_path) and os.path.isdir(views_path):
                    enum_views(views_path, p, 'views')
                else:
                    enum_views(path, p, pattern='views*')
            #deal with settings
            inifile =os.path.join(get_app_dir(p), 'settings.ini')
            if os.path.exists(inifile):
                settings.insert(0, inifile)
           
        modules['views'] = list(views)
        modules['settings'] = settings
        return modules
    
    def install_views(self, views):
        for v in views:
            try:
                myimport(v)
            except Exception, e:
                log.exception(e)
    
    def install_apps(self):
        for p in self.apps:
            try:
                myimport(p)
            except ImportError, e:
                pass
            except Exception, e:
                log.exception(e)
            
    def install_settings(self, s):
        inifile = pkg.resource_filename('uliweb.core', 'default_settings.ini')
        s.insert(0, inifile)
        env = dispatch.get(self, 'init_settings_env')
        conf.settings = Ini(env=env)
        for v in s:
            conf.settings.read(v)
            
    def dispatch_hooks(self):
        #process DISPATCH hooks
        d = conf.settings.get('DISPATCH', None)
        if d:
            hooks = d.get('bind', [])
            if hooks:
                for h in hooks:
                    try:
                        func = h.pop('function')
                    except:
                        log.error("Can't find function in bind option, %r" % h)
                        continue
                    dispatch.bind(**h)(func)
            exposes = d.get('expose', [])
            if exposes:
                for h in exposes:
                    try:
                        func = h.pop('function')
                    except:
                        log.error("Can't find function in bind option, %r" % h)
                        continue
                    expose(**h)(func)
            
    def get_template_dirs(self):
        template_dirs = [os.path.join(get_app_dir(p), 'templates') for p in self.apps]
        return template_dirs
    
    def get_templateplugins_dirs(self):
        return [os.path.join(get_app_dir(p), 'template_plugins') for p in self.apps]
    
    def __call__(self, environ, start_response):
        local.application = self
        local.request = req = Request(environ)
        conf.request = RequestProxy()
        local.response = res = Response(content_type='text/html')
        conf.response = ResponseProxy()
        local.url_adapter = adapter = conf.url_map.bind_to_environ(environ)
        
        try:
            endpoint, values = adapter.match()
            
            mod, handler = self.prepare_request(req, endpoint)
            
            #process static
            if endpoint in conf.static_views:
                response = self.call_view(mod, handler, req, res, **values)
            else:
                response = None
                _clses = {}
                _inss = {}

                #middleware process request
                middlewares = conf.settings.GLOBAL.get('MIDDLEWARE_CLASSES', [])
                s = []
                for middleware in middlewares:
                    try:
                        order = None
                        if isinstance(middleware, tuple):
                            order, middleware = middleware
                        cls = import_func(middleware)
                        if order is None:
                            order = getattr(cls, 'ORDER', 500)
                        s.append((order, middleware))
                    except ImportError, e:
                        log.exception(e)
                        error("Can't import the middleware %s" % middleware)
                    _clses[middleware] = cls
                middlewares = sort_list(s)
                
                for middleware in middlewares:
                    cls = _clses[middleware]
                    if hasattr(cls, 'process_request'):
                        ins = cls(self, conf.settings)
                        _inss[middleware] = ins
                        response = ins.process_request(req)
                        if response is not None:
                            break
                
                if response is None:
                    try:
                        response = self.call_view(mod, handler, req, res, **values)
                        
                    except Exception, e:
                        for middleware in reversed(middlewares):
                            cls = _clses[middleware]
                            if hasattr(cls, 'process_exception'):
                                ins = _inss.get(middleware)
                                if not ins:
                                    ins = cls(self, conf.settings)
                                response = ins.process_exception(req, e)
                                if response:
                                    break
                        else:
                            raise
                        
                else:
                    response = res
                    
                for middleware in reversed(middlewares):
                    cls = _clses[middleware]
                    if hasattr(cls, 'process_response'):
                        ins = _inss.get(middleware)
                        if not ins:
                            ins = cls(self, conf.settings)
                        response = ins.process_response(req, response)
                
            #endif
            
        except HTTPError, e:
            response = self.render(e.errorpage, Storage(e.errors), request=req)
        except NotFound, e:
            response = self.not_found(req, e)
        except InternalServerError, e:
            response = self.internal_error(req, e)
        except HTTPException, e:
            response = e
        return ClosingIterator(response(environ, start_response),
                               [local_manager.cleanup])
