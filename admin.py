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

from settings import *
from models import *
from utils import *

def login(request):
    return HttpResponseRedirect(users.create_login_url(request.META.get("HTTP_REFERER","/")))
    
def logout(request):
    return HttpResponseRedirect(users.create_logout_url(request.META.get("HTTP_REFERER","/")))

def adminerror(request):
    return returnerror("404 查无此人,地址不存在")
  
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
                    return returnjson({"result":ccEscape("没有文件")}, resp)
                
                img_binary = filedata["content"]
                if not img_binary:
                    return returnjson({"result":ccEscape("没有图片数据")}, resp)
                
                if len(img_binary) > 1024*1024:
                    return returnjson({"result":ccEscape("文件大小超过 1M 限制")}, resp)
                
                filename = request.POST.get("Filename")
                if filename != filedata['filename']:
                    return returnjson({"result":ccEscape("POST filename %s != FILES filename %s" %(filename, filedata['filename'])) }, resp)
                
                filename = ccEscape(filename)               
                albumname = ccEscape(request.POST.get("albumname"))
                description = ccEscape(request.POST.get("description",""))
                
                try:
                    owner = users.get_current_user().nickname()
                except:
                    owner = request.POST.get("owner","unknown")
                
                contenttype = getImageType(img_binary)
                if contenttype.find('image')==-1:
                    return returnjson({"result":ccEscape("不支持的文件格式")}, resp)
                
                album = Album.GetAlbumByName(albumname)
                if not album:
                    return returnjson({"result":ccEscape("找不到相册 %s"%albumname)}, resp)
                
                
                photo = savephoto2DB(img_binary,album,filename, description, contenttype, owner)
                if not photo:
                    return returnjson({"result":ccEscape("数据库错误")}, resp)
                logging.info('%s saved to DB'%filename)
                
                res = {}
                res["result"]="ok"
                res["id"] = photo.id
                return returnjson(res, resp)
        
        if checkAuthorization():
            albums = Album.all()
        else:
            return returnerror("你没有上传权限")
        
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
            return HttpResponseRedirect(str(u"/%s/%s"%(photo.album.name, photo2.name)))
        else:
            return HttpResponseRedirect(str(u"/%s"%(photo.album.name)))
        
    return returnerror("照片不存在")

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
        save = (request.POST.get("save"))
        default = (request.POST.get("default"))
        clear = (request.POST.get("clear"))
        clearcache = (request.POST.get("clearcache"))
        
        if save:
            gallery_settings.title = title
            gallery_settings.description = description
            gallery_settings.albums_per_page = albums_per_page
            gallery_settings.thumbs_per_page = thumbs_per_page
            gallery_settings.save()
        elif default:
            defaultSettings()
        elif clear:
            logging.info("清空数据")
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
                           "msg":ccEscape("没有这张照片")}, resp)
                if not photo.album.public and not checkAuthorization():
                    return returnjson({"result":"error",
                           "msg":ccEscape("你没有权限访问这张照片")}, resp)
                
                photo.AddComment(author, comment_content)
                logging.info( buildComments(photo.GetComments()) )
                return returnjson({"result":"ok",
                         "comments": buildComments(photo.GetComments())}, resp)
        
            else:
                return returnjson({"result":"error",
                           "msg":ccEscape("请填写名字和评论内容")}, resp)
        
        if not checkAuthorization():
            return returnjson({"result":"error",
                           "msg":ccEscape("你没有权限")}, resp)
        
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
                                       "msg":ccEscape("没有这张相片"),
                                       }, resp)
            else:
                return returnjson({"result":"error",
                                   "msg":ccEscape("没有这个相册")}, resp)
        
        elif action == "getalbum":
            albumname = ccEscape(request.GET.get('albumname',None))
            album = albumname and Album.GetAlbumByName(albumname)
            if album:
                return returnjson({"result":"ok",
                                   "album":Album2Dict(album),
                                   }, resp)
            else:
                return returnjson({"result":"error",
                                   "msg":ccEscape("没有这个相册")}, resp)
                
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
                                   "msg":ccEscape("没有这个相册")}, resp)
                
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
                                   "msg":ccEscape("没有这个相册")}, resp)
                
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
                                   "msg":ccEscape("没有这个相册")}, resp)
                
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
                                   "msg":ccEscape("没有这张照片")}, resp)
                
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
                                   "msg":ccEscape("没有这条评论")}, resp)
            
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
                return returnerror("同名的相册已存在")
            
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
