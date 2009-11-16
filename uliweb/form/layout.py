__all__ = ['Layout', 'TableLayout', 'CSSLayout', 'YamlLayout']

from html import Buf, Tag

class Layout(object):
    def __init__(self, form, layout=None):
        self.form = form
        self.layout = layout
        
    def html(self):
        return ''
    
    def __str__(self):
        return self.html()
    
    def get_widget_name(self, f):
        return f.build.__name__
    
    def is_hidden(self, f):
        return self.get_widget_name(f) == 'Hidden'
    
class TableLayout(Layout):
    def line(self, label, input, help_string='', error=None):
        tr = Tag('tr')
        tr << Tag('td', label)
        td = tr << Tag('td', input)
        if error:
            td << Tag('br/')
            td << Tag('span', error, _class='error')
        td = tr << Tag('td', help_string)
        return tr

    def single_line(self, element):
        tr = Tag('tr')
        tr << Tag('td', element, colspan=3)
        return tr

    def buttons_line(self, buttons):
        tr = Tag('tr', align='center', _class="buttons")
        td = tr << Tag('td', Tag('label', '&nbsp;', _class='field'), colspan=3)
        td << buttons
        return tr
        
    def html(self):
        buf = Buf()
        buf << self.form.form_begin
        
        p = buf << Tag('fieldset')
        if self.form.form_title:
            p << Tag('legend', self.form.form_title)
        table = p << Tag('table')
        tbody = table << Tag('tbody')

        for name, obj in self.form.fields_list:
            f = getattr(self.form, name)
            if self.is_hidden(obj):
                tbody << f
            else:
                tbody << self.line(f.label, f, f.help_string, f.error)
        
        tbody << self.buttons_line(self.form.get_buttons())
        buf << self.form.form_end
        return str(buf)
    
class CSSLayout(Layout):
    def line(self, obj, label, input, help_string='', error=None):
        div = Buf()
        div << label
        div << input
        if error:
            div << Tag('span', error, _class='error')
        div << Tag('br/')
        return div

    def buttons_line(self, buttons):
        div = Buf()
        div << Tag('label', '&nbsp;', _class='field')
        div << buttons
        div << Tag('br/')
        return div

    def html(self):
        buf = Buf()
        buf << self.form.form_begin
        
        form = buf << Tag('fieldset')
        if self.form.form_title:
            form << Tag('legend', self.form.form_title)
    
        for name, obj in self.form.fields_list:
            f = getattr(self.form, name)
            if self.is_hidden(obj):
                form << f
            else:
                form << self.line(obj, f.label, f, f.help_string, f.error)
        
        form << self.buttons_line(self.form.get_buttons())
        buf << self.form.form_end
        return str(buf)

from widgets import RadioSelect, Radio

class YamlRadioSelect(RadioSelect):
    def html(self):
        s = Buf()
        for v, caption in self.choices:
            args = {'value': v}
            id = args.setdefault('id', 'radio_%d' % self.get_id())
            args['name'] = self.kwargs.get('name')
            if v == self.value:
                args['checked'] = None
            div = Tag('div', _class='type-check')
            div << Radio(**args)
            div << Tag('label', caption, _for=id)
            s << div
        return str(s)
    
class YamlLayout(Layout):
    field_classes = {
        ('Text', 'Password', 'TextArea'):'type-text',
        ('Button', 'Submit', 'Reset'):'type-button',
        ('Select', 'RadioSelect'):'type-select',
        ('Radio', 'Checkbox'):'type-check',
        }

    def get_class(self, f):
        name = f.build.__name__
        _class = 'type-text'
        for k, v in self.field_classes.items():
            if name in k:
                _class = v
                break
        return _class
    
    def line(self, obj, label, input, help_string='', error=None):
        _class = self.get_class(obj)
        if error:
            _class = _class + ' error'
        
        if self.get_widget_name(obj) == 'RadioSelect':
            obj.build = YamlRadioSelect
            fs = Tag('fieldset')
            fs << Tag('legend', label)
            fs << input
            return fs
        else:
            div = Tag('div', _class=_class)
            if error:
                div << Tag('strong', error, _class="message")
            if self.get_widget_name(obj) == 'Checkbox':
                div << input
                div << label
            else:
                div << label
                div << input
            return div

    def buttons_line(self, buttons):
        div = Tag('div', _class='type-button')
        div << buttons
        return div

    def html(self):
        buf = Buf()
        if 'yform' not in self.form.html_attrs['_class']:
            self.form.html_attrs['_class'] = 'yform'
        buf << self.form.form_begin
        
        form = buf << Tag('fieldset')
        if self.form.form_title:
            form << Tag('legend', self.form.form_title)
    
        for name, obj in self.form.fields_list:
            f = getattr(self.form, name)
            if self.is_hidden(obj):
                form << f
            else:
                form << self.line(obj, f.label, f, f.help_string, f.error)
        
        buf << self.buttons_line(self.form.get_buttons())
        buf << self.form.form_end
        return str(buf)
