# -*- coding: utf-8 -*-

import logging

from datetime import datetime
import time

from google.appengine.ext import db  
from google.appengine.api import users
from google.appengine.api import images
from google.appengine.api import memcache
from google.appengine.api import urlfetch

from django.http import HttpResponse,HttpResponseRedirect
from django.utils.html import escape
from django.utils import text
from django.shortcuts import render_to_response

from cc_addons.language import * 
from settings import *
from models import *
from utils import *
    
def index(request):
    global gallery_settings
    if not gallery_settings:
        gallery_settings = InitGallery()
        
    try:
        page_index = int(request.GET["page"])
    except:
        page_index = 1
        
    lang = request.GET.get("lang")
    if lang:
        save_current_lang(lang)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER','/'))
    
         
    if checkAuthorization():
        try:
            albums = Album.all().order("-updatedate")
            entries,pager = CCPager(query=albums,items_per_page=gallery_settings.albums_per_page).fetch(page_index)
        except:
            albums = Album.all()
            entries,pager = CCPager(query=albums,items_per_page=gallery_settings.albums_per_page).fetch(page_index)
    else:
        try:
            albums = Album.GetPublicAlbums().order("-updatedate")
            entries,pager = CCPager(query=albums,items_per_page=gallery_settings.albums_per_page).fetch(page_index)
        except:
            albums = Album.GetPublicAlbums()
            entries,pager = CCPager(query=albums,items_per_page=gallery_settings.albums_per_page).fetch(page_index)
        
    content = {"albums":entries,
               "pager": pager}
    return render_to_response_with_users_and_settings("index.html", content)

def album(request, albumname):
    try:
        page_index = int(request.GET['page'])
    except:
        page_index = 1
        
    album = Album.GetAlbumByName(ccEscape(albumname))
    if album:
        if not album.public and not checkAuthorization():
                return returnerror(translate("You are not authorized"))
        
        try:    
            photos = album.GetPhotos()
            entries,pager = CCPager(query=photos,items_per_page=gallery_settings.thumbs_per_page).fetch(page_index)
        except:
            photos = Photo.all().filter("album =", album)
            entries,pager = CCPager(query=photos,items_per_page=gallery_settings.thumbs_per_page).fetch(page_index)
    else:
        return returnerror(translate("Album does not exist"))
            
    content = {"album":album,
               "photos":entries,
               "pager": pager}
    
    return render_to_response_with_users_and_settings("album.html", content)

def photo(request, albumname, photoname):
    album = Album.GetAlbumByName(ccEscape(albumname))
    if album:
        if not album.public and not checkAuthorization():
            return returnerror(translate("You are not authorized to access this photo"))
        
        photo = album.GetPhotoByName(ccEscape(photoname))
        if not photo:
            return returnerror(translate("Photo does not exist"))
    else:
        return returnerror(translate("Album does not exist"))
    
    if request.POST:
        author = ccEscape(request.POST.get("comment_author"))
        content = ccEscape(request.POST.get("comment_content"))
        photo.AddComment(author, content)
        return HttpResponseRedirect((u"/%s/%s"%(albumname,photoname )).encode("utf-8"))
        
    current = album.photoslist.index(photo.id)
    total = album.photoCount
    prevphoto = None
    if current:
        prevphoto = Photo.GetPhotoByID(album.photoslist[current-1])
    nextphoto = None
    try:
        nextphoto = Photo.GetPhotoByID(album.photoslist[current+1])
    except:
        pass
    
    content = {"album":album,
               "photo":photo,
               "prevphoto":prevphoto,"nextphoto":nextphoto,
               "current":current+1,"total":total,
               }
    return render_to_response_with_users_and_settings("photo.html", content)

def showslider(request, albumname):
    album = Album.GetAlbumByName(ccEscape(albumname))
    if album:
        if not album.public and not checkAuthorization():
                return returnerror(translate("You are not authorized"))
        try:    
            photos = album.GetPhotos()
        except:
            photos = album.GetPhotos("")
    else:
        return returnerror(translate("Album does not exist"))
            
    content = {"album":album,
               "photos":photos,
               }
    return render_to_response_with_users_and_settings("slider.html", content)

def showimage(request, photoid):
    resp = HttpResponse()
    try:
        key = "image_%s"%(long(photoid))
        
        cachedata = memcache.get(key)
        if cachedata:
            if not cachedata['public'] and not checkAuthorization():
                return returnerror(translate("You are not authorized"))
            
            resp.headers['Content-Type'] = cachedata['Content-Type']
            resp.write(cachedata['binary'])
            return resp
        
        photo = Photo.GetPhotoByID(long(photoid))
        if not photo.album.public and not checkAuthorization():
                return returnerror(translate("You are not authorized"))
            
        resp.headers['Content-Type'] = photo.contenttype
        resp.write(photo.binary)
        
        cachedata = {'Content-Type':photo.contenttype,
                     'binary':photo.binary,
                     'public':photo.album.public}
        memcache.set(key, cachedata, 20*24*3600)
        return resp
    except:
        url = "http://%s/static/images/error.gif"%os.environ["HTTP_HOST"]
        result = urlfetch.fetch(url, deadline=10)
        if result.status_code == 200:
            resp.headers['Content-Type'] = result.headers['Content-Type']
            resp.write(result.content)
            return resp
        return returnerror(translate("Get photo error"))

def showthumb(request, photoid):
    resp = HttpResponse()
    try:
        resp.headers['Content-Type'] = "image/png"
        
        key = "thumb_%s"%(long(photoid))
        cachedata = memcache.get(key)
        
        if cachedata:
            if not cachedata['public'] and not checkAuthorization():
                return returnerror(translate("You are not authorized"))
            resp.write(cachedata['binary'])
            return resp
            
        photo = Photo.GetPhotoByID(long(photoid))
        if not photo.album.public and not checkAuthorization():
                return returnerror(translate("You are not authorized"))
            
        binary_thumb = photo.binary_thumb
        if not binary_thumb:
            img = images.Image(photo.binary)
            img.resize(200, 200)
            binary_thumb = img.execute_transforms()
            
        resp.write(binary_thumb)

        cachedata = {'binary':binary_thumb,
                     'public':photo.album.public}
        memcache.set(key, cachedata, 20*24*3600)
        
        return resp
    except:
        url = "http://%s/static/images/error.gif"%os.environ["HTTP_HOST"]
        result = urlfetch.fetch(url, deadline=10)
        if result.status_code == 200:
            resp.headers['Content-Type'] = result.headers['Content-Type']
            resp.write(result.content)
            return resp
        return returnerror(translate("Get photo error"))

