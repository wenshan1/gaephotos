from uliweb.utils.common import log, check_apps_dir, is_pyfile_exist

def action_syncdb(apps_dir):
    def action():
        """create all models according all available apps"""
        check_apps_dir(apps_dir)

        from uliweb.core.SimpleFrame import get_apps, get_app_dir, Dispatcher
        from uliweb import orm
        app = Dispatcher(apps_dir=apps_dir, start=False)
        orm.set_auto_create(False)
        db = orm.get_connection(app.settings.ORM.CONNECTION)
        
        models = []
        for p in get_apps(apps_dir):
            if not is_pyfile_exist(get_app_dir(p), 'models'):
                continue
            m = '%s.models' % p
            try:
                mod = __import__(m, {}, {}, [''])
                models.append(mod)
            except ImportError:
                log.exception()
        
        db.metadata.create_all()
            
    return action

def action_reset(apps_dir):
    def action(appname=''):
        """Reset the appname models(drop and recreate)"""
        check_apps_dir(apps_dir)

        if not appname:
            appname = ''
            while not appname:
                appname = raw_input('Please enter app name:')
        
        from uliweb.core.SimpleFrame import get_app_dir, Dispatcher
        from uliweb import orm
        app = Dispatcher(apps_dir=apps_dir, start=False)
        orm.set_auto_create(False)
        db = orm.get_connection(app.settings.ORM.CONNECTION)

        if not is_pyfile_exist(get_app_dir(appname), 'models'):
            return
        m = '%s.models' % appname
        try:
            mod = __import__(m, {}, {}, [''])
        except ImportError:
            log.exception()
        
        db.metadata.drop_all()
        db.metadata.create_all()
            
    return action

class MockDBAPI(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.paramstyle = 'named'
    def connect(self, **kwargs):
        print kwargs, self.kwargs
        for k in self.kwargs:
            assert k in kwargs, "key %s not present in dictionary" % k
            assert kwargs[k]==self.kwargs[k], "value %s does not match %s" % (kwargs[k], self.kwargs[k])
        return MockConnection()
class MockConnection(object):
    def close(self):
        pass
    def cursor(self):
        return MockCursor()
    def run_callable(self, do):
        print 'xxxxxxxxxxxxxxxx'
        False
class MockCursor(object):
    def close(self):
        pass

def action_sql(apps_dir):
    def action(appname=''):
        """Display the table creation sql statement"""
        check_apps_dir(apps_dir)
        
        from uliweb.core.SimpleFrame import get_apps, get_app_dir, Dispatcher
        from uliweb import orm
        from StringIO import StringIO
        from sqlalchemy import create_engine
        
        app = Dispatcher(apps_dir=apps_dir, start=False)
        orm.set_auto_create(False)
        p = app.settings.ORM.CONNECTION
        _engine = p[:p.find('://')+3]
        con = create_engine(_engine, strategy='mock', executor=lambda s, p='': buf.write(s + p))
        db = orm.get_connection(con)

        buf = StringIO()
        apps = get_apps(apps_dir)
        if appname:
            apps_list = [appname]
        else:
            apps_list = apps[:]
        models = []
        for p in apps_list:
            if p not in apps:
                log.error('Error: Appname %s is not a valid app' % p)
                continue
            if not is_pyfile_exist(get_app_dir(p), 'models'):
                continue
            m = '%s.models' % p
            try:
                mod = __import__(m, {}, {}, [''])
                models.append(mod)
            except ImportError:
                log.exception()
        
        db.metadata.create_all(db)
        print buf.getvalue()
    return action
