import os
from uliweb.core.dispatch import bind
from uliweb.core.SimpleFrame import expose
from werkzeug.exceptions import Forbidden

__all__ = ['save_file', 'get_filename', 'get_url']

@bind('startup_installed')
def install(sender):
    url = sender.settings.UPLOAD.URL_SUFFIX.rstrip('/')
    expose('%s/<path:filename>' % url, static=True)(file_serving)
 
@bind('prepare_view_env')
def prepare_view_env(sender, env, request):
    d = get_url
    def g(application):
        def f(filename, path_to=None, subfolder='', application=application):
            return d(filename, path_to=path_to, subfolder=subfolder, application=application)
        return f
    env['get_url'] = g(request.application)

def file_serving(filename):
    from uliweb.utils.filedown import filedown
    from uliweb.utils import files
    from uliweb.core.SimpleFrame import local
    
    fname = _get_normal_filename(filename, application=application)
    s = application.settings.GLOBAL
    fname = files.encoding_filename(fname, s.HTMLPAGE_ENCODING, s.FILESYSTEM_ENCODING)
    return filedown(local.request.environ, fname)
    
def _get_normal_filename(filename, path_to=None, subfolder='', application=None):
    path = path_to or application.settings.UPLOAD.TO_PATH
    if subfolder:
        path = os.path.join(path, subfolder).replace('\\', '/')
    fname = os.path.normpath(filename)
    f = os.path.join(path, fname).replace('\\', '/')
    if not f.startswith(path):
        raise Forbidden("You can not visit unsafe files.")
    return f

def save_file(filename, fobj, path_to=None, replace=False, subfolder='', application=None):
    from uliweb.utils import files
    assert hasattr(fobj, 'read'), "fobj parameter should be a file-like object"
    fname = _get_normal_filename(filename, path_to, subfolder, application=application)
    s = application.settings.GLOBAL
    fname = files.encoding_filename(fname, s.HTMLPAGE_ENCODING, s.FILESYSTEM_ENCODING)
    
    filename = files.save_file(fname, fobj, replace, application.settings.UPLOAD.BUFFER_SIZE)
    return files.encoding_filename(filename, s.FILESYSTEM_ENCODING, s.HTMLPAGE_ENCODING)

def save_file_field(field, path_to=None, replace=False, subfolder='', application=None):
    if field:
        filename = field.data.filename
        fname = save_file(filename, field.data.file, path_to, replace, subfolder, application)
        field.data.filename = fname
        
def save_image_field(field, path_to=None, resize_to=None, replace=False, subfolder='', application=None):
    if field:
        if resize_to:
            from uliweb.utils.image import resize_image
            field.data.file = resize_image(field.data.file, resize_to)
        filename = field.data.filename
        fname = save_file(filename, field.data.file, path_to, replace, subfolder, application)
        field.data.filename = fname
        
def get_filename(filename, path_to=None, subfolder='', application=None):
    return _get_normal_filename(filename, path_to, subfolder, application)

def get_url(filename, path_to=None, subfolder='', application=None):
    import urllib
    filename = urllib.quote_plus(filename)
    return _get_normal_filename(filename, application.settings.UPLOAD.URL_SUFFIX, subfolder, application)
