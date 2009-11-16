from models import User
from uliweb.core.dispatch import bind, LOW
from uliweb.utils.common import log

@bind('get_user', signal=(None, 'default'), kind=LOW)
def get_user(request, user_id):
    return User.get(user_id)

@bind('authenticate', signal=(None, 'default'), kind=LOW)
def authenticate(request, username, password):
    user = User.get(User.c.username==username)
    if user:
        if user.check_password(password):
            return True, user, 'default'
        else:
            return False, {'password': "Password isn't correct!"}, 'default'
    else:
        return False, {'username': 'Username is not existed!'}, 'default'
    
@bind('create_user', signal=(None, 'default'), kind=LOW)
def create_user(request, username, password, **kwargs):
    try:
        user = User.get(User.c.username==username)
        if user:
            return False, {'username':"Username is already existed!"}
        user = User(username=username, password=password)
        user.set_password(password)
        user.save()
        return True, user
    except Exception, e:
        log.exception(e)
        return False, {'_': "Creating user failed!"}
    
@bind('delete_user', signal=(None, 'default'), kind=LOW)
def delete_user(request, username):
    return True

@bind('change_password', signal=(None, 'default'), kind=LOW)
def change_password(request, username, password):
    user = User.get(User.c.username==username)
    user.set_password(password)
    user.save()
    return True

@bind('login', signal=(None, 'default'), kind=LOW)
def login(request, username):
    return True

@bind('logout', signal=(None, 'default'), kind=LOW)
def logout(request, username):
    return True
