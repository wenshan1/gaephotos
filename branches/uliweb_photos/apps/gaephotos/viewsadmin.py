#coding=utf-8

import time

from google.appengine.api import users
from google.appengine.api import images
from google.appengine.api import memcache
from google.appengine.api import urlfetch

from werkzeug.utils import http_date
from uliweb import expose
from uliweb.core.dispatch import bind
from uliweb.core.SimpleFrame import Response
from uliweb.utils.filedown import _generate_etag

from models import *
from languages import translate,save_current_lang
import ccutils
from ccutils import *
from comm import *



@expose('/admin/album/')
@requires_site_admin
def albummanage():
    if request.POST:
        new = request.POST.get("createalbum")
        if new:  #create album
            new_name = ccEscape(request.POST.get("new_name"))
            new_public = request.POST.get("new_public")
            if new_public == "true":
                new_public = True
            else:
                new_public = False
                
            new_description = ccEscape(request.POST.get("new_description"))
            
            if Album.CheckAlbumExist(new_name):
                return returnerror(translate("Album exist with this name"))
            
            album = Album()
            album.name = new_name
            album.public = new_public
            album.description = new_description
            album.save()
            
        return redirect("/admin/album/")
    
    albums = Album.all()        
    content = {"albums": albums,
               }
    response.template = 'admin/album_manage.html'
    return content

