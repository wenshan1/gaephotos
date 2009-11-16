from html import Tag

class Build(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def html(self):
        raise NotImplementedError

    def __str__(self):
        return self.html()

class Text(Build):
    type = 'text'

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def html(self):
        args = self.kwargs.copy()
        args.setdefault('type', self.type)
        return str(Tag('input', **args))

class Password(Text): type = 'password'
class TextArea(Build):
    def __init__(self, value='', **kwargs):
        self.kwargs = kwargs
        self.value = value

    def html(self):
        args = self.kwargs
        args.setdefault('rows', 5)
        args.setdefault('cols', 40)
        return str(Tag('textarea', self.value, **args))
class Hidden(Text): type = 'hidden'
class Button(Text): type = 'button'
class Submit(Text): type = 'submit'
class Reset(Text): type = 'reset'
class File(Text): type = 'file'
class Radio(Text): type = 'radio'
class Select(Build):
    def __init__(self, choices, value=None, **kwargs):
        self.choices = choices
        self.value = value
        self.kwargs = kwargs

    def html(self):
        s = []
        for v, caption in self.choices:
            args = {'value': v}
            if v == self.value:
                args['selected'] = None
            s.append(str(Tag('option', caption, **args)))
        return str(Tag('select', '\n'.join(s), **self.kwargs))
    
class RadioSelect(Select):
    _id = 0
    def __init__(self, choices, value=None, **kwargs):
        Select.__init__(self, choices, value, **kwargs)

    def html(self):
        s = []
        for v, caption in self.choices:
            args = {'value': v}
            id = args.setdefault('id', 'radio_%d' % self.get_id())
            args['name'] = self.kwargs.get('name')
            if v == self.value:
                args['checked'] = None
            s.append(str(Radio(**args)))
            s.append(str(Tag('label', caption, _for=id)))
        return ''.join(s)
    
    def get_id(self):
        RadioSelect._id += 1
        return self._id
    
class Checkbox(Build):
    def __init__(self, value=False, **kwargs):
        self.value = value
        self.kwargs = kwargs

    def html(self):
        args = self.kwargs.copy()
        if self.value:
            args.setdefault('checked', None)
        args.setdefault('type', 'checkbox')
        return str(Tag('input', **args))
