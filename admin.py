# -*- coding: utf-8 -*-

from datetime import datetime
import time

from google.appengine.ext import db  
from google.appengine.api import users
from google.appengine.api import images
from google.appengine.api import memcache

from django.http import HttpResponse,HttpResponseRedirect
from django.utils.html import escape
from django.utils import text,simplejson
from django.shortcuts import render_to_response

from cc_addons.language import translate 
from settings import *
from models import *
from utils import *

def login(request):
    return HttpResponseRedirect(users.create_login_url(request.META.get("HTTP_REFERER","/")))
    
def logout(request):
    return HttpResponseRedirect(users.create_logout_url(request.META.get("HTTP_REFERER","/")))

def adminerror(request):
    return returnerror(translate("Room 404, nobody living here"))
  
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


def localjavascript(request, scriptname):
    return render_to_javasript('localjavascript/%s.js'%scriptname,{})

#@requires_site_admin 
# FIXME: swfupload can not pass users cookie in firefox, so the
# is_current_user_admin return False in the swfupload request always  
def swfuploadphoto(request):
    try:
        if request.POST:
            if request.FILES:
                resp = HttpResponse()
                #resp.headers['Content-Type'] = "application/json"
                
                
                filedata = request.FILES.get("Filedata",None)
                if not filedata:
                    return returnjson({"result":ccEscape(translate("no upload file"))}, resp)
                
                img_binary = filedata["content"]
                if not img_binary:
                    return returnjson({"result":ccEscape(translate("no image data"))}, resp)
                
                if len(img_binary) > 1024*1024:
                    return returnjson({"result":ccEscape(translate("file size exceed 1M"))}, resp)
                
                filename = request.POST.get("Filename")
                if filename != filedata['filename']:
                    return returnjson({"result":ccEscape("POST filename %s != FILES filename %s" %(filename, filedata['filename'])) }, resp)
                
                if filename.find(" ") != -1:
                    return returnjson({"result":ccEscape(translate("filename can not contain space"))}, resp)
                filename = ccEscape(filename)               
                albumname = ccEscape(request.POST.get("albumname"))
                description = ccEscape(request.POST.get("description",""))
                
                try:
                    owner = users.get_current_user().nickname()
                except:
                    owner = request.POST.get("owner","unknown")
                
                contenttype = getImageType(img_binary)
                if contenttype.find('image')==-1:
                    return returnjson({"result":ccEscape(translate("unsupported file type"))}, resp)
                
                album = Album.GetAlbumByName(albumname)
                if not album:
                    return returnjson({"result":ccEscape("%s %s"%(translate("Album does not exist"),albumname))}, resp)
                
                
                photo = savephoto2DB(img_binary,album,filename, description, contenttype, owner)
                if not photo:
                    return returnjson({"result":ccEscape(translate("Database error"))}, resp)
                logging.info('%s saved to DB'%filename)
                
                res = {}
                res["result"]="ok"
                res["id"] = photo.id
                return returnjson(res, resp)
        
        if checkAuthorization():
            albums = Album.all()
        else:
            return returnerror(translate("You are not authorized to upload"))
        
        content = {
                   "albums": albums,
                   }
        return render_to_response_with_users_and_settings('admin/swfupload.html',content)
    except Exception,e:
        logging.exception("upload error "+str(e))
        
@requires_site_admin
def delphoto(request, photoid):
    photo = Photo.GetPhotoByID(long(photoid))
    if photo:
        photoslist = photo.album.photoslist
        index = (photoslist.index(photo.id)+1) % len(photoslist)
        photo2 = Photo.GetPhotoByID(photoslist[index])
        photo.Delete()
        if photo2:
            return HttpResponseRedirect((u"/%s/%s"%(photo.album.name, photo2.name)).encode("utf-8"))
        else:
            return HttpResponseRedirect((u"/%s"%(photo.album.name)).encode("utf-8"))
        
    return returnerror(translate("Photo does not exist"))

def defaultSettings():
    global gallery_settings
    #gallery_settings.domain=os.environ["HTTP_HOST"]
    #gallery_settings.baseurl="http://"+gallery_settings.domain
    gallery_settings.title = "GAE Photos"
    gallery_settings.description = "Photo gallery based on GAE"
    gallery_settings.albums_per_page = 8
    gallery_settings.thumbs_per_page = 12
    gallery_settings.save()
    
@requires_site_admin
def settings(request):
    global gallery_settings
    if request.POST:
        title = ccEscape(request.POST.get("title"))
        description = ccEscape(request.POST.get("description"))
        albums_per_page = int(request.POST.get("albums_per_page"))
        thumbs_per_page = int(request.POST.get("thumbs_per_page"))
        adminlist = ccEscape(request.POST.get("adminlist"))
        save = (request.POST.get("save"))
        default = (request.POST.get("default"))
        clear = (request.POST.get("clear"))
        clearcache = (request.POST.get("clearcache"))
        
        if save:
            gallery_settings.title = title
            gallery_settings.description = description
            gallery_settings.albums_per_page = albums_per_page
            gallery_settings.thumbs_per_page = thumbs_per_page
            gallery_settings.adminlist = adminlist
            gallery_settings.save()
        elif default:
            defaultSettings()
        elif clear:
            logging.info("clean all data")
            for comment in Comment.all():
                comment.delete()
            for photo in Photo.all():
                photo.delete()
            for album in Album.all():
                album.delete()
        elif clearcache:
            memcache.flush_all()
        else:
            pass
        
    content = {"cachestats": memcache.get_stats()
               }
    return render_to_response_with_users_and_settings('admin/settings.html',content)    

#@requires_site_admin
def ajaxAction(request):
    try:
        resp = HttpResponse()
        
        action = request.GET.get('action',None)
        logging.info(action)
        
        if action == "addcomment":
            photoid = long(request.GET.get('photoid',None))
            author = ccEscape(request.GET.get('author',None))
            comment_content = ccEscape(request.GET.get('comment_content',None))
            if photoid and author and comment_content:
                photo = Photo.get_by_id(photoid)
                if not photo:
                    return returnjson({"result":"error",
                           "msg":ccEscape(translate("Photo does not exist"))}, resp)
                if not photo.album.public and not checkAuthorization():
                    return returnjson({"result":"error",
                           "msg":ccEscape(translate("You are not authorized to access this photo"))}, resp)
                
                photo.AddComment(author, comment_content)
                logging.info( buildComments(photo.GetComments()) )
                return returnjson({"result":"ok",
                         "comments": buildComments(photo.GetComments())}, resp)
        
            else:
                return returnjson({"result":"error",
                           "msg":ccEscape(translate("Pls input name and content"))}, resp)
        
        if not checkAuthorization():
            return returnjson({"result":"error",
                           "msg":ccEscape(translate("You are not authorized"))}, resp)
        
        if action == "setcoverphoto":
            albumid = long(request.GET.get('albumid',0))
            album = albumid and Album.get_by_id(albumid)
            if album:
                id = long(request.GET.get('photoid',0))
                photo = id and Photo.GetPhotoByID(id)
                if photo:
                    album.SetCoverPhoto(photo.id)
                    return returnjson({"result":"ok",
                                       }, resp)
                else:
                    return returnjson({"result":"error",
                                       "msg":ccEscape(translate("Photo does not exist")),
                                       }, resp)
            else:
                return returnjson({"result":"error",
                                   "msg":ccEscape(translate("Album does not exist"))}, resp)
        
        elif action == "getalbum":
            albumname = ccEscape(request.GET.get('albumname',None))
            album = albumname and Album.GetAlbumByName(albumname)
            if album:
                return returnjson({"result":"ok",
                                   "album":Album2Dict(album),
                                   }, resp)
            else:
                return returnjson({"result":"error",
                                   "msg":ccEscape(translate("Album does not exist"))}, resp)
                
        elif action == "savealbum":
            id = long(request.GET.get('albumid',0))
            album = id and Album.GetAlbumByID(id)
            if album:
                albumname = ccEscape(request.GET.get('albumname',None))
                description = ccEscape(request.GET.get('description',None))  
                coverphotoid = long(request.GET.get('coverphotoid',0))
                public = request.GET.get("public")
                if public == "true":
                    public = True
                else:
                    public = False
                    
                album.name = albumname
                album.description = description
                album.public = public
                album.save()
                if coverphotoid:
                    album.SetCoverPhoto(coverphotoid)
                    
                return returnjson({"result":"ok",
                                   "album":Album2Dict(album),
                                   }, resp)
            else:
                return returnjson({"result":"error",
                                   "msg":ccEscape(translate("Album does not exist"))}, resp)
                
        elif action == "clearalbum":
            id = long(request.GET.get('albumid',0))
            album = id and Album.GetAlbumByID(id)
            if album:
                for photo in album.GetPhotos():
                    photo.Delete()
                album = Album.GetAlbumByID(id)
                return returnjson({"result":"ok",
                                   "album":Album2Dict(album),
                                   }, resp)
            else:
                return returnjson({"result":"error",
                                   "msg":ccEscape(translate("Album does not exist"))}, resp)
                
        elif action == "deletealbum":
            id = long(request.GET.get('albumid',0))
            album = id and Album.GetAlbumByID(id)
            if album:
                for photo in album.GetPhotos():
                    photo.Delete()
                album = Album.GetAlbumByID(id)
                album.delete()
                album = Album.all().fetch(1)
                album = album and album[0]
                return returnjson({"result":"ok",
                                   "album":Album2Dict(album),
                                   }, resp)
            else:
                return returnjson({"result":"error",
                                   "msg":ccEscape(translate("Album does not exist"))}, resp)
                
        elif action == "savephotodesp":
            id = long(request.GET.get('photoid',0))
            photo = id and Photo.GetPhotoByID(id)
            if photo:
                description = ccEscape(request.GET.get('description',None))
                photo.description = description
                photo.Save()
                return returnjson({"result":"ok",
                                   "description":photo.description,
                                   }, resp)
            else:
                return returnjson({"result":"error",
                                   "msg":ccEscape(translate("Photo does not exist"))}, resp)
                
        elif action == "deletecomment":
            id = long(request.GET.get('commentid',0))
            comment = id and Comment.get_by_id(id)
            photoid = comment.photo.id
            if comment:
                comment.Delete()
#                return returnjson({"result":"ok",
#                                   "commentid":id,
#                                   }, resp)
                photo = Photo.get_by_id(photoid)
                return returnjson({"result":"ok",
                         "comments": buildComments(photo.GetComments())}, resp)
            else:
                return returnjson({"result":"error",
                                   "msg":ccEscape(translate("Comment does not exist"))}, resp)
            
        return returnjson({"result":"error",
                           "msg":ccEscape("no action")}, resp)
    except Exception,e:
        return returnjson({"result":"error",
                           "msg":str(e)}, resp)

@requires_site_admin
def albummanage(request):
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
            
        return HttpResponseRedirect("/admin/album/")
    
    albums = Album.all()        
    content = {"albums": albums,
               }
    return render_to_response_with_users_and_settings('admin/album_manage.html',content)   