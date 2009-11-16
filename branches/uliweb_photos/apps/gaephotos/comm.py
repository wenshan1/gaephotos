#coding=utf-8

from functools import wraps

from google.appengine.api import users
from uliweb.core.SimpleFrame import Response
from uliweb.core.template import render_file
from ccutils import *
from models import *

def checkAuthorization():
    user = users.get_current_user()
    if not user:
        return False
    
    email = user.email()
    adminlist = gallery_settings.adminlist.split(";")
    try:
        adminlist.remove("")
    except:
        pass
    
    for admin in adminlist:
        if admin == email:
            return True
    
    if users.is_current_user_admin():
        return True
    
    return False

def requires_site_admin(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        if not checkAuthorization():
            return returnerror(translate("You are not authorized"))
        else:
            return method(*args, **kwargs)
    return wrapper 


def returnerror(msg):
    content = {'error_msg':msg}
    response.template = 'admin/error.html'
    return content