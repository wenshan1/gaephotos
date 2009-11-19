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
# Purpose: admin views for GAEPhotos
# Created: 11/15/2009
#===============================================================================

import logging

from google.appengine.api import memcache

from uliweb import expose,json
from uliweb.core.SimpleFrame import Response

from comm import *
from models import *
from ccutils import *
from languages import translate,save_current_lang


@expose('/localjavascript/<path:scriptname>.js')
def localjavascript(scriptname):
    return render_to_javasript('localjavascript/%s.js'%scriptname,{})


@expose('/admin/settings/')
@requires_site_admin
def globalsettings():
    global gallery_settings
    if request.POST:
        title = ccEscape(request.POST.get("title"))
        description = ccEscape(request.POST.get("description"))
        albums_per_page = int(request.POST.get("albums_per_page"))
        thumbs_per_page = int(request.POST.get("thumbs_per_page"))
        latest_photos_count = int(request.POST.get("latest_photos_count"))
        latest_comments_count = int(request.POST.get("latest_comments_count"))
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
            gallery_settings.latest_photos_count = latest_photos_count
            gallery_settings.latest_comments_count = latest_comments_count
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
            memcache.flush_all()
        elif clearcache:
            memcache.flush_all()
        else:
            pass
        
    content = {"cachestats": ccDict(memcache.get_stats())}
    response.template = 'admin/globalsettings.html'
    return content  

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

@requires_site_admin
@expose('/admin/delphoto/<photoid>')
def delphoto(photoid):
    photo = Photo.GetPhotoByID(long(photoid))
    if photo:
        photoslist = photo.album.photoslist
        index = (photoslist.index(photo.id)+1) % len(photoslist)
        photo2 = Photo.GetPhotoByID(photoslist[index])
        photo.Delete()
        if photo2:
            return redirect((u"/%s/%s"%(photo.album.name, photo2.name)).encode("utf-8"))
        else:
            return redirect((u"/%s"%(photo.album.name)).encode("utf-8"))
        
    return returnerror(translate("Photo does not exist"))

#@requires_site_admin 
# FIXME: swfupload can not pass users cookie in firefox, so the
# is_current_user_admin return False in the swfupload request always  
@expose('/admin/uploadphoto/')
def swfuploadphoto():
    try:
        if request.POST:
            if request.FILES:
                resp = Response()
                #resp.headers['Content-Type'] = "application/json"
                
                
                filedata = request.FILES.get("Filedata",None)
                if not filedata:
                    return returnjson({"result":ccEscape(translate("no upload file"))}, resp)
                
                img_binary = filedata.stream
                if not img_binary:
                    return returnjson({"result":ccEscape(translate("no image data"))}, resp)
                
                if filedata.content_length > 1024*1024:
                    return returnjson({"result":ccEscape(translate("file size exceed 1M"))}, resp)
                
                filename = request.POST.get("Filename")
                if filename != filedata.filename:
                    return returnjson({"result":ccEscape("POST filename %s != FILES filename %s" %(filename, filedata.filename)) }, resp)
                
                if filename.find(" ") != -1:
                    return returnjson({"result":ccEscape(translate("filename can not contain space"))}, resp)
                filename = ccEscape(filename)               
                albumname = ccEscape(request.POST.get("albumname"))
                description = ccEscape(request.POST.get("description",""))
                
                try:
                    owner = users.get_current_user().nickname()
                except:
                    owner = request.POST.get("owner","unknown")
                
                img_binary = filedata.read()
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
        response.template = 'admin/swfupload.html'
        return content
    
    except Exception,e:
        logging.exception("upload error "+str(e))
        resp = Response()
        return returnjson({"result":("exception in swfuploadphoto")}, resp)

@json
@expose('/admin/ajaxaction/addcomment/')
def addComment():
    logging.info("addcomment")
    
    photoid = long(request.GET.get('photoid',None))
    author = ccEscape(request.GET.get('author',None))
    comment_content = ccEscape(request.GET.get('comment_content',None))
    if photoid and author and comment_content:
        photo = Photo.get_by_id(photoid)
        if not photo:
            return {"result":"error",
                   "msg":ccEscape(translate("Photo does not exist"))}
        if not photo.album.public and not checkAuthorization():
            return {"result":"error",
                   "msg":ccEscape(translate("You are not authorized to access this photo"))}
        
        photo.AddComment(author, comment_content)
        logging.info( buildcomments(photo.GetComments()) )
        return {"result":"ok",
                 "comments": buildcomments(photo.GetComments())}

    else:
        return {"result":"error",
                   "msg":ccEscape(translate("Pls input name and content"))}
   
def saveCoverPhoto():
    albumid = long(request.GET.get('albumid',0))
    album = albumid and Album.get_by_id(albumid)
    if album:
        id = long(request.GET.get('photoid',0))
        photo = id and Photo.GetPhotoByID(id)
        if photo:
            album.SetCoverPhoto(photo.id)
            return {"result":"ok",}
        else:
            return {"result":"error",
                         "msg":ccEscape(translate("Photo does not exist")),}
    else:
        return {"result":"error",
                     "msg":ccEscape(translate("Album does not exist")),}

        
def getAlbumInfo():
    albumname = ccEscape(request.GET.get('albumname',None))
    album = albumname and Album.GetAlbumByName(albumname)
    if album:
        return {"result":"ok",
                           "album":album2dict(album),
                           }
    else:
        return {"result":"error",
                           "msg":ccEscape(translate("Album does not exist"))}
    
    
def saveAlbumInfo():
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
            
        return {"result":"ok",
                      "album":album2dict(album),}
    else:
        return {"result":"error",
                     "msg":ccEscape(translate("Album does not exist")),}

def clearAlbumPhotos():
    id = long(request.GET.get('albumid',0))
    album = id and Album.GetAlbumByID(id)
    if album:
        for photo in album.GetPhotos():
            photo.Delete()
        album = Album.GetAlbumByID(id)
        return {"result":"ok",
                           "album":album2dict(album),
                           }
    else:
        return {"result":"error",
                           "msg":ccEscape(translate("Album does not exist"))}
    
def deleteAlbum():
    id = long(request.GET.get('albumid',0))
    album = id and Album.GetAlbumByID(id)
    if album:
        for photo in album.GetPhotos():
            photo.Delete()
        album = Album.GetAlbumByID(id)
        album.delete()
        album = Album.all().fetch(1)
        album = album and album[0]
        return {"result":"ok",
                           "album":album2dict(album),
                           }
    else:
        return {"result":"error",
                           "msg":ccEscape(translate("Album does not exist"))}
    
    
def savePhotoDescription():
    id = long(request.GET.get('photoid',0))
    photo = id and Photo.GetPhotoByID(id)
    if photo:
        description = ccEscape(request.GET.get('description',None))
        photo.description = description
        photo.Save()
        return {"result":"ok",
                    "description": (photo.description),}
    else:
        return {"result":"error",
                     "msg":ccEscape(translate("Photo does not exist"))}
    
    
def deleteComment():
    id = long(request.GET.get('commentid',0))
    comment = id and Comment.get_by_id(id)
    photoid = comment.photo.id
    if comment:
        comment.Delete()
        photo = Photo.get_by_id(photoid)
        return {"result":"ok",
                     "comments": buildcomments(photo.GetComments())}
    else:
        return {"result":"error",
                     "msg":ccEscape(translate("Comment does not exist"))}
    
@json
@expose('/admin/ajaxaction/')
def ajaxAction():
    try:
        resp = Response()
        
        action = request.GET.get('action',None)
        logging.info(action)
        
        
        if not checkAuthorization():
            return returnjson({"result":"error",
                           "msg":ccEscape(translate("You are not authorized"))}, resp)
        
        if action == "setcoverphoto":
            return saveCoverPhoto()
        
        elif action == "getalbum":
            return getAlbumInfo()
                
        elif action == "savealbum":
            return saveAlbumInfo()
                
        elif action == "clearalbum":
            return clearAlbumPhotos()
                
        elif action == "deletealbum":
            return deleteAlbum()
                
        elif action == "savephotodesp":
            return savePhotoDescription()
                
        elif action == "deletecomment":
            return deleteComment()
            
        return {"result":"error",
                     "msg":ccEscape("no action")}
    
    except Exception,e:
        logging.exception(str(e))
        return {"result":"error",
                     "msg":str(e)}


def defaultSettings():
    global gallery_settings
    #gallery_settings.domain=os.environ["HTTP_HOST"]
    #gallery_settings.baseurl="http://"+gallery_settings.domain
    gallery_settings.title = "GAE Photos"
    gallery_settings.description = "Photo gallery based on GAE"
    gallery_settings.albums_per_page = 8
    gallery_settings.thumbs_per_page = 12
    gallery_settings.latest_photos_count = 9
    gallery_settings.latest_comments_count = 5
    gallery_settings.save()
