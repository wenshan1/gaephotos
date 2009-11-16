#coding=utf-8
import os
import sys
from common import log

def save_file(fname, fobj, replace=False, buffer_size=4096):
    assert hasattr(fobj, 'read'), "fobj parameter should be a file-like object"
    path = os.path.dirname(fname)
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except Exception, e:
            log.exception(e)
            raise Exception("Can't create %s directory" % path)
    
    if not replace:
        ff, ext = os.path.splitext(fname)
        i = 1
        while os.path.exists(fname):
            fname = ff+'('+str(i)+')'+ext
            i += 1
        
    out = open(fname, 'wb')
    try:
        while 1:
            text = fobj.read(buffer_size)
            if text:
                out.write(text)
            else:
                break
        return os.path.basename(fname)
    finally:
        out.close()
        
def encoding_filename(filename, from_encoding='utf-8', to_encoding=None):
    """
    >>> print encoding_filename('\xe4\xb8\xad\xe5\x9b\xbd.doc')
    \xd6\xd0\xb9\xfa.doc
    >>> f = unicode('\xe4\xb8\xad\xe5\x9b\xbd.doc', 'utf-8')
    >>> print encoding_filename(f)
    \xd6\xd0\xb9\xfa.doc
    >>> print encoding_filename(f.encode('gbk'))
    \xd6\xd0\xb9\xfa.doc
    """
    import sys
    to_encoding = to_encoding or sys.getfilesystemencoding()
    from_encoding = from_encoding or sys.getfilesystemencoding()
    if not isinstance(filename, unicode):
        try:
            f = unicode(filename, from_encoding)
        except UnicodeDecodeError:
            try:
                f = unicode(filename, 'utf-8')
            except UnicodeDecodeError:
                try:
                    f = unicode(filename, to_encoding)
                except UnicodeDecodeError:
                    raise Exception, "Unknown encoding of the filename %s" % filename
        filename = f
    return filename.encode(to_encoding)
