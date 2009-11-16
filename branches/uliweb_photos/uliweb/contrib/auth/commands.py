from uliweb.utils.common import check_apps_dir

def action_createsuperuser(apps_dir):
    def action():
        """create a super user account"""
        check_apps_dir(apps_dir)

        from uliweb.core.SimpleFrame import Dispatcher
        from uliweb import orm
        from getpass import getpass
        
        app = Dispatcher(apps_dir=apps_dir, start=False)
        orm.set_auto_create(True)
        db = orm.get_connection(app.settings.ORM.CONNECTION)
        
        username = ''
        while not username:
            username = raw_input("Please enter the super user's name: ")
        email = ''
        while not email:
            email = raw_input("Please enter the email of [%s]: " % username)
            
        password = ''
        while not password:
            password = getpass("Please enter the password for [%s(%s)]: " % (username, email))
        repassword = ''
        while not repassword:
            repassword = getpass("Please enter the password again: ")
        
        if password != repassword:
            print "The password is not matched, can't create super user!"
            return
        
        from models import User
        user = User(username=username, email=email)
        user.set_password(password)
        user.is_superuser = True
        user.save()
        
    return action

