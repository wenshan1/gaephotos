#!/usr/bin/env python
import sys, os
import logging
from uliweb.utils.common import log, check_apps_dir, timeit
import uliweb as conf
        
apps_dir = 'apps'

workpath = os.path.join(os.path.dirname(__file__), 'lib')
if workpath not in sys.path:
    sys.path.insert(0, os.path.join(workpath, 'lib'))

from werkzeug import script
from uliweb.core import SimpleFrame

def install_config(apps_dir):
    from uliweb.utils import pyini
    #user can configure custom PYTHONPATH, so that uliweb can add these paths
    #to sys.path, and user can manage third party or public apps in a separate
    #directory
    config_filename = os.path.join(apps_dir, 'config.ini')
    if os.path.exists(config_filename):
        c = pyini.Ini(config_filename)
        paths = c.GLOBAL.get('PYTHONPATH', [])
        if paths:
            for p in reversed(paths):
                p = os.path.abspath(os.path.normpath(p))
                if not p in sys.path:
                    sys.path.insert(0, p)
                    
def set_log(app):
    if app.settings.LOG:
        level = app.settings.LOG.get("level", "info").upper()
    else:
        level = 'INFO'
    log.setLevel(getattr(logging, level, logging.INFO))

def make_application(debug=None, apps_dir='apps', include_apps=None, debug_console=True):
    from uliweb.utils.common import sort_list
    
    if apps_dir not in sys.path:
        sys.path.insert(0, apps_dir)
        
    install_config(apps_dir)
    
    application = app = SimpleFrame.Dispatcher(apps_dir=apps_dir, include_apps=include_apps)
    
    #settings global application object
    conf.application = app
    
    #set logger level
    set_log(app)
    
    if app.settings.GLOBAL.WSGI_MIDDLEWARES:
        s = sort_list(app.settings.GLOBAL.WSGI_MIDDLEWARES, default=500)
        for w in reversed(s):
            if w in app.settings:
                args = app.settings[w].dict()
            else:
                args = None
            if args:
                klass = args.pop('CLASS', None) or args.pop('class', None)
                if not klass:
                    log.error('Error: There is no a CLASS option in this WSGI Middleware [%s].' % w)
                    continue
                modname, clsname = klass.rsplit('.', 1)
                try:
                    mod = __import__(modname, {}, {}, [''])
                    c = getattr(mod, clsname)
                    app = c(app, **args)
                except Exception, e:
                    log.exception(e)
                
    debug_flag = application.settings.GLOBAL.DEBUG
    if debug or debug_flag:
        log.setLevel(logging.DEBUG)
        log.info(' * Loading DebuggedApplication...')
        from werkzeug.debug import DebuggedApplication
        app = DebuggedApplication(app, debug_console)
    return app

def make_app(appname=''):
    """create a new app according the appname parameter"""

    if not appname:
        appname = ''
        while not appname:
            appname = raw_input('Please enter app name:')
        
    ans = '-1'
    if os.path.exists(apps_dir):
        path = os.path.join(apps_dir, appname)
    else:
        path = appname
    
    if os.path.exists(path):
        while ans not in ('y', 'n'):
            ans = raw_input('The app directory has been existed, do you want to overwrite it?(y/n)[n]')
            if not ans:
                ans = 'n'
    else:
        ans = 'y'
    if ans == 'y':
        from uliweb.utils.common import extract_dirs
        extract_dirs('uliweb', 'template_files/app', path)

def make_pkg(pkgname=''):
    """create a new python package folder according the appname parameter"""

    if not pkgname:
        pkgname = ''
        while not pkgname:
            pkgname = raw_input('Please enter python package name:')
        
    if not os.path.exists(pkgname):
        os.makedirs(pkgname)
    initfile = os.path.join(pkgname, '__init__.py')
    if not os.path.exists(initfile):
        f = open(initfile, 'w')
        f.close()

def make_project(project_name='', verbose=('v', False)):
    """create a new project directory according the project name"""
    from uliweb.utils.common import extract_dirs
    
    if not project_name:
        project_name = ''
        while not project_name:
            project_name = raw_input('Please enter project name:')

    ans = '-1'
    if os.path.exists(project_name):
        while ans not in ('y', 'n'):
            ans = raw_input('The project directory has been existed, do you want to overwrite it?(y/n)[n]')
            if not ans:
                ans = 'n'
    else:
        ans = 'y'
    if ans == 'y':
        extract_dirs('uliweb', 'template_files/project', project_name)
    
def exportstatic(outputdir=('o', ''), verbose=('v', False), check=True):
    """
    Export all installed apps' static directory to outputdir directory.
    """
    check_apps_dir(apps_dir)

    from uliweb.utils.common import copy_dir_with_check

    if not outputdir:
        log.error("Error: outputdir should be a directory and can't be empty")
        sys.exit(0)

    application = SimpleFrame.Dispatcher(apps_dir=apps_dir, start=False)
    apps = application.apps
    dirs = [os.path.join(SimpleFrame.get_app_dir(appname), 'static') for appname in apps]
    copy_dir_with_check(dirs, outputdir, verbose, check)
    
def extracturls(urlfile='urls.py'):
    """
    Extract all url mappings from view modules to a specified file.
    """
    check_apps_dir(apps_dir)

    application = SimpleFrame.Dispatcher(apps_dir=apps_dir, use_urls=False, start=False)
    filename = os.path.join(application.apps_dir, urlfile)
    if os.path.exists(filename):
        answer = raw_input("Error: [%s] is existed already, do you want to overwrite it(y/n):" % urlfile)
        if answer.strip() != 'y':
            return
    f = file(filename, 'w')
    print >>f, "from uliweb.core.rules import Mapping, add_rule\n"
    print >>f, "url_map = Mapping()"
    application.url_infos.sort()
    for url, kw in application.url_infos:
        endpoint = kw.pop('endpoint')
        if kw:
            s = ['%s=%r' % (k, v) for k, v in kw.items()]
            t = ', %s' % ', '.join(s)
        else:
            t = ''
        print >>f, "add_rule(url_map, %r, %r%s)" % (url, endpoint, t)
    f.close()

def collcet_commands():
    from uliweb import get_apps
    actions = {}
    for f in get_apps(apps_dir):
        m = '%s.commands' % f
        try:
            mod = __import__(m, {}, {}, [''])
        except ImportError:
            continue
        
        for t in dir(mod):
            if t.startswith('action_') and callable(getattr(mod, t)):
                actions[t] = getattr(mod, t)(apps_dir)
    return actions

def call_commands(command='', appname=('a', '')):
    """
    Call <command>.py for each installed app according the command argument.
    """
    if not command:
        log.error("Error: There is no command module name behind call command.")
        return
    if not appname:
        from uliweb import get_apps
        apps = get_apps(apps_dir)
    else:
        apps = [appname]
    actions = {}
    for f in apps:
        m = '%s.%s' % (f, command)
        try:
            mod = __import__(m, {}, {}, [''])
        except ImportError:
            continue
                
def collect_files(apps_dir, apps):
    files = [os.path.join(apps_dir, 'settings.ini')]
    
    def f(path):
        for r in os.listdir(path):
            if r in ['.svn', '_svn']:
                continue
            fpath = os.path.join(path, r)
            if os.path.isdir(fpath):
                f(fpath)
            else:
                ext = os.path.splitext(fpath)[1]
                if ext in ['.py', '.ini']:
                    files.append(fpath)
    
    from uliweb import get_app_dir
    for p in apps:
        path = get_app_dir(p)
        files.append(os.path.join(path, 'config.ini'))
        files.append(os.path.join(path, 'settings.ini'))
        f(path)
    return files
        
def runserver(apps_dir, hostname='localhost', port=5000, 
            threaded=False, processes=1, admin=False):
    """Returns an action callback that spawns a new wsgiref server."""
    def action(hostname=('h', hostname), port=('p', port), reload=True, debugger=True,
               threaded=threaded, processes=processes):
        """Start a new development server."""
        check_apps_dir(apps_dir)

        from werkzeug.serving import run_simple
        from uliweb import get_apps

        if admin:
            include_apps = ['uliweb.contrib.admin']
            app = make_application(debugger, apps_dir, 
                        include_apps=include_apps)
        else:
            app = make_application(debugger, apps_dir)
            include_apps = []
        extra_files = collect_files(apps_dir, get_apps(apps_dir)+include_apps)
        run_simple(hostname, port, app, reload, False, True,
                   extra_files, 1, threaded, processes)
    return action

    
def main():
    global apps_dir

    apps_dir = os.path.join(os.getcwd(), apps_dir)
    if os.path.exists(apps_dir):
        sys.path.insert(0, apps_dir)
       
    install_config(apps_dir)
    
    action_runserver = runserver(apps_dir, port=8000)
    action_runadmin = runserver(apps_dir, port=8000, admin=True)
    action_makeapp = make_app
    action_makepkg = make_pkg
    action_exportstatic = exportstatic
    from uliweb.i18n.i18ntool import make_extract
    action_i18n = make_extract(apps_dir)
    action_extracturls = extracturls
    action_makeproject = make_project
    action_call = call_commands
    
    #process app's commands.py
    locals().update(collcet_commands())

    script.run()

if __name__ == '__main__':
    main()