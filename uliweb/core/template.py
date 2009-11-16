#! /usr/bin/env python
#coding=utf-8

import re
import os

__templates_temp_dir = 'tmp/templates_temp'
__options = {'use_temp_dir':False}

def use_tempdir(dir=''):
    global __options, __templates_temp_dir
    
    if dir:
        __templates_temp_dir = dir
        __options['use_temp_dir'] = True
        if not os.path.exists(__templates_temp_dir):
            os.makedirs(__templates_temp_dir)

def set_options(**options):
    """
    default use_temp_dir=False
    """
    __options.update(options)

def get_temp_template(filename):
    if __options['use_temp_dir']:
        f, filename = os.path.splitdrive(filename)
        filename = filename.replace('\\', '_')
        filename = filename.replace('/', '_')
        return os.path.normcase(os.path.join(__templates_temp_dir, filename))
    return filename

def reindent(text):
    lines=text.split('\n')
    new_lines=[]
    credit=k=0
    for raw_line in lines:
        line=raw_line.strip()
        if line[:5]=='elif ' or line[:5]=='else:' or    \
            line[:7]=='except:' or line[:7]=='except ' or \
            line[:7]=='finally:':
                k=k+credit-1
        if k<0: k=0
        new_lines.append('    '*k+line)
        credit=0
        if line=='pass' or line[:5]=='pass ':
            credit=0
            k-=1
        if line=='return' or line[:7]=='return ' or \
            line=='continue' or line[:9]=='continue ' or \
            line=='break' or line[:6]=='break':
            credit=1
            k-=1
        if line[-1:]==':' or line[:3]=='if ':
            k+=1
    text='\n'.join(new_lines)
    return text

def get_templatefile(filename, dirs, default_template=None):
    if os.path.exists(filename):
        return filename
    if filename:
        if dirs:
            for d in dirs:
                path = os.path.join(d, filename)
                if os.path.exists(path):
                    return path
    if default_template:
        if isinstance(default_template, (list, tuple)):
            for i in default_template:
                f = get_templatefile(i, dirs)
                if f:
                    return f
        else:
            return get_templatefile(default_template, dirs)

r_tag = re.compile(r'(\{\{.*?\}\})', re.DOTALL|re.M)

class Node(object):
    block = 0
    var = False
    def __init__(self, value=None):
        self.value = value
        
    def __str__(self):
        if self.value:
            return self.value
        else:
            return ''
    
class BlockNode(Node):
    def __init__(self, name='', parent=None):
        self.nodes = []
        self.parent = parent
        if self.parent:
            self.vars = self.parent.vars
        else:
            self.vars = {}
        self.name = name
        
    def add(self, node):
        self.nodes.append(node)
        if isinstance(node, BlockNode):
            self.vars[node.name] = node
        
    def merge(self, content):
        self.nodes.extend(content.nodes)
        self.vars.update(content.vars)
        
    def clear_content(self):
        self.nodes = []
    
    def __str__(self):
        s = []
        for x in self.nodes:
            if isinstance(x, BlockNode) and x.name in self.vars:
                s.append(str(self.vars[x.name]))
            else:
                s.append(str(x))
        return ''.join(s)

class Content(BlockNode):
    def __init__(self):
        self.nodes = []
        self.vars = {}

class ContextPopException(Exception):
    "pop() has been called more times than push()"
    pass

class Context(object):
    "A stack container for variable context"
    def __init__(self, dict_=None):
        dict_ = dict_ or {}
        self.dicts = [dict_]
        self.dirty = True
        self.result = None

    def __repr__(self):
        return repr(self.dicts)

    def __iter__(self):
        for d in self.dicts:
            yield d

    def push(self):
        d = {}
        self.dicts = [d] + self.dicts
        self.dirty = True
        return d

    def pop(self):
        if len(self.dicts) == 1:
            raise ContextPopException
        return self.dicts.pop(0)
        self.dirty = True

    def __setitem__(self, key, value):
        "Set a variable in the current context"
        self.dicts[0][key] = value
        self.dirty = True

    def __getitem__(self, key):
        "Get a variable's value, starting at the current context and going upward"
        for d in self.dicts:
            if key in d:
                return d[key]
        raise KeyError(key)

    def __delitem__(self, key):
        "Delete a variable from the current context"
        del self.dicts[0][key]
        self.dirty = True

    def has_key(self, key):
        for d in self.dicts:
            if key in d:
                return True
        return False

    __contains__ = has_key

    def get(self, key, otherwise=None):
        for d in self.dicts:
            if key in d:
                return d[key]
        return otherwise

    def update(self, other_dict):
        "Like dict.update(). Pushes an entire dictionary's keys and values onto the context."
        if not hasattr(other_dict, '__getitem__'): 
            raise TypeError('other_dict must be a mapping (dictionary-like) object.')
        self.dicts = [other_dict] + self.dicts
        self.dirty = True
        return other_dict
    
    def to_dict(self):
        if not self.dirty:
            return self.result
        else:
            d = {}
            for i in reversed(self.dicts):
                d.update(i)
            self.result = d
            self.dirty = False
        return d
        
class Lexer(object):
    def __init__(self, text, vars=None, env=None, dirs=None, handlers=None):
        self.text = text
        self.vars = vars or {}
        if not isinstance(env, Context):
            env = Context(env)
        self.env = env
        self.dirs = dirs
        self.writer = 'out.write'
        self.handlers = handlers or {}
        self.content = Content()
        self.stack = [self.content]
        self.parse(text)
        
    def output(self):
        return str(self.content)
        
    def parse(self, text):
        in_tag = False
        extend = None  #if need to process extend node
        for i in r_tag.split(text):
            if i:
                if len(self.stack) == 0:
                    raise Exception, "The 'end' tag is unmatched, please check if you spell 'block' right"
                top = self.stack[-1]
                if in_tag:
                    line = i[2:-2].strip()
                    if not line:
                        continue
                    if line.startswith('='):
                        name, value = '=', line[1:].strip()
                    elif line.startswith('<<'):
                        name, value = '<<', line[2:].strip()
                    else:
                        v = line.split(' ', 1)
                        if len(v) == 1:
                            name, value = v[0], ''
                        else:
                            name, value = v
                    if name in self.handlers:
                        self.handlers[name](value, top, self.stack, self.vars, self.env, self.dirs, self.writer)
                    elif name == 'block':
                        node = BlockNode(name=value.strip(), parent=top)
                        top.add(node)
                        self.stack.append(node)
                    elif name == 'end':
                        self.stack.pop()
                    elif name == '=':
                        buf = "\n%s(%s)\n" % (self.writer, value)
                        top.add(buf)
                    elif name == '<<':
                        buf = "\n%s(%s, escape=False)\n" % (self.writer, value)
                        top.add(buf)
                    elif name == 'include':
                        self._parse_include(top, value)
                    elif name == 'extend':
                        extend = value
                    else:
                        if line and in_tag:
                            top.add(line)
                else:
                    buf = "\n%s(%r, escape=False)\n" % (self.writer, i)
                    top.add(buf)
                    
            in_tag = not in_tag
        if extend:
            self._parse_extend(extend)
            
    def _parse_include(self, content, filename):
        if not filename.strip():
            return
        filename = eval(filename, self.env.to_dict(), self.vars)
        fname = get_templatefile(filename, self.dirs)
        if not fname:
            raise Exception, "Can't find the template %s" % filename
        
        f = open(fname, 'rb')
        text = f.read()
        f.close()
        t = Lexer(text, self.vars, self.env, self.dirs, self.handlers)
        content.merge(t.content)
        
    def _parse_extend(self, filename):
        filename = eval(filename, self.env.to_dict(), self.vars)
        fname = get_templatefile(filename, self.dirs)
        if not fname:
            raise Exception, "Can't find the template %s" % filename
        
        f = open(fname, 'rb')
        text = f.read()
        f.close()
        self.env.push()
        t = Lexer(text, self.vars, self.env, self.dirs, self.handlers)
        self.content.clear_content()
        t.content.merge(self.content)
        self.content = t.content
 
def render_text(text, vars=None, env=None, dirs=None, default_template=None, handlers=None):
    dirs = dirs or ['.']
    content = Lexer(text, vars, Context(env), dirs, handlers=handlers)
    return reindent(content.output()), content.env

def render_file(filename, vars=None, env=None, dirs=None, default_template=None, use_temp=False, handlers=None):
    fname = get_templatefile(filename, dirs, default_template)
    if not fname:
        raise Exception, "Can't find the template %s" % filename
    if use_temp:
        f = get_temp_template(fname)
        if os.path.exists(f):
            if os.path.getmtime(f) >= os.path.getmtime(fname):
                return fname, file(f, 'rb').read()
    text, e = render_text(file(fname).read(), vars, env, dirs, default_template, handlers)
    if use_temp:
        f = get_temp_template(fname)
        try:
            fo = file(f, 'wb')
            fo.write(text)
            fo.close()
        except:
            pass
    return fname, text, e

def template_file(filename, vars=None, env=None, dirs=None, default_template=None, handlers=None):
    fname, code, e = render_file(filename, vars, env, dirs, default_template, use_temp=__options['use_temp_dir'], handlers=handlers)
    return _run(code, vars, e, fname)

def template(text, vars=None, env=None, dirs=None, default_template=None, handlers=None):
    code, e = render_text(text, vars, env, dirs, default_template, handlers=handlers)
    return _run(code, vars, e)

import StringIO
import cgi

class Out(object):
    encoding = 'utf-8'
    
    def __init__(self):
        self.buf = StringIO.StringIO()
        
    def _str(self, text):
        if not isinstance(text, (str, unicode)):
            text = str(text)
        if isinstance(text, unicode):
            return text.encode(self.encoding)
        else:
            return text

    def write(self, text, escape=True):
        s = self._str(text)
        if escape:
            self.buf.write(cgi.escape(s))
        else:
            self.buf.write(s)
            
    def noescape(self, text):
        self.write(self._str(text), escape=False)
        
#    def json(self, text):
#        from datawrap import dumps
#        self.write(dumps(text))
#
    def getvalue(self):
        return self.buf.getvalue()

def _prepare_run(vars, env, out):
    def f(_vars, _env):
        def defined(v):
            try:
                return v in _vars or v in _env
            except:
                return False
        return defined
    e = {}
    if isinstance(env, Context):
        new_e = env.to_dict()
    else:
        new_e = env
    e.update(new_e)
    e.update(vars)
    e['out'] = out
    e['xml'] = out.noescape
    e['_vars'] = vars
    e['defined'] = f(vars, new_e)
    e['_env'] = e
    return e
    
def _run(code, locals=None, env=None, filename='template'):
    out = Out()
    locals = locals or {}
    env = env or {}
    e = _prepare_run(locals, env, out)
    
    if isinstance(code, (str, unicode)):
        code = compile(code, filename, 'exec')
    exec code in e
    return out.getvalue()

def test():
    """
    >>> print template("Hello, {{=name}}", {'name':'uliweb'})
    Hello, uliweb
    >>> print template("Hello, {{ =name}}", {'name':'uliweb'})
    Hello, uliweb
    >>> print template("Hello, {{ = name}}", {'name':'uliweb'})
    Hello, uliweb
    >>> print template("Hello, {{=name}}", {'name':'<h1>Uliweb</h1>'})
    Hello, &lt;h1&gt;Uliweb&lt;/h1&gt;
    >>> print template("Hello, {{<<name}}", {'name':'<h1>Uliweb</h1>'})
    Hello, <h1>Uliweb</h1>
    >>> print template('''{{import datetime}}{{=datetime.date( # this breaks
    ...   2009,1,8)}}''')
    2009-01-08
    """

if __name__ == '__main__':
    print template("Hello, {{=name}}", {'name':'uliweb'})