#coding=utf-8
#===============================================================================
# Copyright 2009 Chao Chen
# Licensed under the Apache License, Version 2.0 (the "License"); 
# you may not use this file except in compliance with the License. 
# You may obtain a copy of the License at 
# http://www.apache.org/licenses/LICENSE-2.0 
# Unless required by applicable law or agreed to in writing, 
# software distributed under the License is distributed on an "AS IS" BASIS, 
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
# See the License for the specific language governing permissions and 
# limitations under the License. 
#
# Author:  CChen <deepgully@gmail.com> 
# Purpose: common functions for GAEPhotos
# Created: 11/15/2009
#===============================================================================

import simplejson

from google.appengine.api import users
from google.appengine.api import images

from uliweb.core.SimpleFrame import Response
from uliweb.core.template import render_file
from uliweb.utils.common import wraps
from uliweb.core.template import template_file

from ccutils import *
from models import *
from languages import translate,save_current_lang


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
    from uliweb import response
    response.template = 'admin/error.html'
    return content

def returnjson(dit,response):
    #response.headers['Content-Type'] = "application/json"
    response.write(simplejson.dumps(dit))
    return response 

def render_to_javasript(*args, **kwargs):
    from uliweb import application
    resp = Response()
    resp.headers['Content-Type'] = "text/javascript"
    resp.write(application.template(*args, **kwargs))
    return resp

def render_to_atom(*args, **kwargs):
    from uliweb import application
    resp = Response()
    resp.headers['Content-Type'] = "application/atom+xml"
    resp.write(application.template(*args, **kwargs))
    return resp

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
    admin = checkAuthorization()
    for comment in comments:
        li.append({'author':comment.author, 'content':ccBreakLines(comment.content),
                   'date':ccFormatDate(comment.date), 'id':comment.id,
                   'admin':admin,})
    return li

def savephoto2DB(binary,album,filename, description, contenttype, owner):
    img = images.Image(binary)
        
    photo = album.GetPhotoByName(filename)
    if not photo:
        photo = Photo()
    photo.album = album
    photo.name = filename
    photo.size = len(binary)
    photo.description = description
    photo.width = img.width
    photo.height = img.height
    photo.contenttype = contenttype
    photo.binary = binary
    photo.mime = contenttype
    photo.owner = owner
    photo.Save()
    
    img.resize(200, 200)
    try:
        photo.binary_thumb = img.execute_transforms()
        photo.save()
    except:
        pass
    return photo

