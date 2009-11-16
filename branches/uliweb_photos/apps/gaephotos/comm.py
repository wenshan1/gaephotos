#coding=utf-8

from functools import wraps

import simplejson

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

def returnjson(dit,response):
    #response.headers['Content-Type'] = "application/json"
    response.write(simplejson.dumps(dit))
    return response 

def album2dict(album):
    if not album:
        return {}
    return {"id": album.id,
            "name":album.name,
            "description": ccUnEscape(album.description),
            "public":album.public,
            "createdate":ccFormatDate(album.createdate),
            "updatedate":ccFormatDate(album.updatedate),
            "photoslist":album.photoslist, 
            "coverphotoid": album.coverPhotoID,}
    
def buildcomments(comments):
    li = []
    for comment in comments:
        li.append({'author':comment.author, 'content':comment.content,
                   'date':ccFormatDate(comment.date), 'id':comment.id,
                   'admin':users.is_current_user_admin(),})
    return li