__all__ = ['u_str', 'Buf', 'Tag']

import cgi

DEFAULT_CHARSET = 'utf-8'

##################################################################
#  HTML Helper
##################################################################

def u_str(v, encoding=None):
    if not encoding:
        encoding = DEFAULT_CHARSET
    if isinstance(v, str):
        pass
    elif isinstance(v, unicode):
        v = v.encode(encoding)
    else:
        v = str(v)
    return v

def _create_kwargs(args, nocreate_if_none=['id', 'for']):
    """
    Make python dict to k="v" format
    
    >>> print _create_kwargs({'name':'title'})
     name="title"
    >>> print _create_kwargs({'_class':'color', 'id':'title'})
     class="color" id="title"
    >>> print _create_kwargs({'_class':'color', 'id':None})
     class="color"
    >>> print _create_kwargs({'_class':'color', 'checked':None})
     class="color" checked
    >>> print _create_kwargs({'_class':'color', '_for':None})
     class="color"
    
    """
    if not args:
        return ''
    s = ['']
    for k, v in sorted(args.items()):
        if k.startswith('_'):
            k = k[1:]
        if v is None:
            if k not in nocreate_if_none:
                s.append(k)
        else:
            s.append('%s="%s"' % (k, cgi.escape(u_str(v))))
    return ' '.join(s)

class Buf(object):
    def __init__(self, begin='', end=''):
        self.buf = []
        self.begin = begin
        self.end = end

    def __lshift__(self, obj):
        if obj:
            if isinstance(obj, (tuple, list)):
                self.buf.extend(obj)
            else:
                self.buf.append(obj)
                obj = [obj]
            return obj[0]
        else:
            return None

    def __str__(self):
        return self.html()

    def html(self):
        s = [self.begin]
        s.extend(self.buf)
        s.append(self.end)
        s = filter(None, s)
        return '\n'.join([str(x) for x in s])

class Tag(Buf):
    """
    Creating a tag. For example:
        
        >>> print Tag('br/').html()
        <br/>
        >>> print Tag('a', 'Hello', href="/")
        <a href="/">
        Hello
        </a>
    """
    def __init__(self, tag, *children, **args):
        self.tag = tag
        self.buf = list(children)
        if tag.endswith('/'):
            self.begin = '<%s%s>' % (tag, _create_kwargs(args))
            self.end = ''
        else:
            self.begin = '<%s%s>' % (tag, _create_kwargs(args))
            self.end = '</%s>' % tag

    def html(self):
        if not self.tag.endswith('/'):
            b = ''.join([u_str(x) for x in self.buf])
            if not b:
                s = [self.begin+self.end]
            else:
                s = [self.begin, b, self.end]
        else:
            s = [self.begin]
        return '\n'.join(s)

