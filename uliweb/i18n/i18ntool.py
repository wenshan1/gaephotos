import os
from uliweb.core import SimpleFrame
from uliweb.utils.common import pkg

#def getfiles(path):
#    files_list = []
#    if os.path.exists(os.path.abspath(os.path.normcase(path))):
#        if os.path.isfile(path):
#            files_list.append(path)
#        else:
#            for root, dirs, files in os.walk(path):
#                for f in files:
#                    filename = os.path.join(root, f)
#                    if '.svn' in filename or (not filename.endswith('.py') and not filename.endswith('.html') and not filename.endswith('.ini')):
#                        continue
#                    files_list.append(filename)
#    return files_list

def _get_outputfile(path, locale='en'):
    output = os.path.normpath(os.path.join(path, 'locale', locale, 'LC_MESSAGES', 'uliweb.pot'))
    return output

def _process(path, locale):
    from pygettext import extrace_files
    from po_merge import merge

    output = _get_outputfile(path, locale=locale)
    try:
        extrace_files(path, output)
        print 'Success! output file is %s' % output
        merge(output[:-4]+'.po', output)
    except:
        raise
    

def make_extract(apps_directory):
    apps_dir = apps_directory
    def action(appname=('a', ''), project=False, apps=False, core=False, locale=('l', 'en')):
        """
        extract i18n message catalog form app or all apps
        """
        path = ''
        if appname:
            _process(SimpleFrame.get_app_dir(appname), locale)
        elif project:
            _process(os.path.normpath(apps_dir + '/..'), locale)
        elif apps:
            _apps = SimpleFrame.get_apps(apps_dir)
            for appname in _apps:
                path = SimpleFrame.get_app_dir(appname)
                if not path.startswith(apps_dir):
                    continue
                _process(SimpleFrame.get_app_dir(appname), locale)
        elif core:
            path = pkg.resource_filename('uliweb', '')
            _process(path, locale)
            
    return action

