import os
import re
from uliweb.core.dispatch import bind
from uliweb.utils.common import log

_saved_template_plugins_modules = {}

def _parse_arguments(text, key='with'):
    r = re.compile(r'\s+%s\s+' % key)
    b = r.split(text)
    if len(b) == 1:
        name, args = b[0], ()
    else:
        name = b[0]
        args = b[1]
    return name, args

def eval_vars(vs, vars, env):
    if isinstance(vs, (tuple, list)):
        return [eval_vars(x, vars, env) for x in vs]
    else:
        return eval(vs, vars, env.to_dict())

from uliweb.utils.sorteddict import SortedDict
def use_tag_handler(app):
    """
    This tag will register a {{use "template_plugin_mmodule" [with arg1[, arg2]]}}
    to template. 
    """
    def use(plugin, container, stack, vars, env, dirs, writer, app=app):
        from uliweb.core.SimpleFrame import get_app_dir
        
        plugin, args = _parse_arguments(plugin)
        plugin = eval_vars(plugin, vars, env)
        args = eval_vars(args, vars, env)
        collection = env.dicts[0].get('collection', SortedDict())
        if plugin in _saved_template_plugins_modules:
            mod = _saved_template_plugins_modules[plugin]
        else:
            from uliweb.utils.common import is_pyfile_exist
            mod = None
            for p in app.apps:
                if not is_pyfile_exist(os.path.join(get_app_dir(p), 'template_plugins'), plugin):
                    continue
                module = '.'.join([p, 'template_plugins', plugin])
                try:
                    mod = __import__(module, {}, {}, [''])
                except ImportError, e:
                    log.exception(e)
                    mod = None
            if mod:
                _saved_template_plugins_modules[plugin] = mod
            else:
                log.debug("Can't found the [%s] html plugins, please check if you've installed special app already" % plugin)
        call = getattr(mod, 'call', None)
        if call:
            v = call(app, vars, env, *args)
            if v:
                collection[plugin] = v
        env['collection'] = collection
    return use

__id = 0
def link_tag_handler(app):
    """
    This tag will register a {{link "link"}} or {{link ["link", "link"] to toplinks}}
    to template. 
    """
    def link(links, container, stack, vars, env, dirs, writer, app=app):
        from uliweb.contrib.staticfiles import url_for_static
        global __id
        
        links, args = _parse_arguments(links, key='to')
        links = eval_vars(links, vars, env)
#        args = eval_vars(args, vars, env)
        collection = env.dicts[0].get('collection', SortedDict())
        if not isinstance(links, (tuple, list)):
            links = [links]
        new_links = [url_for_static(x) for x in links]
        if not args:
            args = 'bottomlinks'
        else:
            args = args
        collection[__id] = {args:new_links}
        __id += 1
        env['collection'] = collection
    return link

@bind('startup_installed')
def startup(sender):
    from uliweb.core import template
    if sender.settings.TEMPLATE.USE_TEMPLATE_TEMP_DIR:
        template.use_tempdir(sender.settings.TEMPLATE.TEMPLATE_TEMP_DIR)

@bind('get_template_tag_handlers')
def get_template_tag_handlers(sender, handlers):
    handlers['use'] = use_tag_handler(sender)
    handlers['link'] = link_tag_handler(sender)

@bind('after_render_template')
def after_render_template(sender, text, vars, env):
    from htmlmerger import merge
    collections = []
    for i in env.dicts:
        if 'collection' in i:
            collections.append(i['collection'])
    return merge(text, collections, vars, env.to_dict())