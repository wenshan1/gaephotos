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

@pagecache("index")
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
    
    albums = get_all_albums()
    entries,pager = CCPager(query=albums,items_per_page=gallery_settings.albums_per_page).fetch(page_index)
     
    public = not checkAuthorization()
    latestcomments = Comment.GetLatestComments(gallery_settings.latest_comments_count, public)
    latestphotos = Photo.GetLatestPhotos(gallery_settings.latest_photos_count, public)
        
    content = {"albums":entries,
               "pager": pager,
               "allalbums":albums,
               "latestcomments": latestcomments,
               "latestphotos": latestphotos}
    return render_to_response_with_users_and_settings("index.html", content)

@pagecache("album")
def album(request, albumname):
    try:
        page_index = int(request.GET['page'])
    except:
        page_index = 1
        
    album = Album.GetAlbumByName(ccEscape(albumname))
    if not album:
        return returnerror(translate("Album does not exist"))
    
    if not album.public and not checkAuthorization():
        return returnerror(translate("You are not authorized"))
    
    photos = album.GetPhotosQuery()
    entries,pager = CCPager(query=photos,items_per_page=gallery_settings.thumbs_per_page).fetch(page_index)
                 
    content = {"album":album,
               "photos":entries,
               "pager": pager,
               "allalbums":get_all_albums(),
               }
    
    return render_to_response_with_users_and_settings("album.html", content)

@pagecache("photo")
def photo(request, albumname, photoname):
    if albumname=="search":
        photo = Photo.GetPhotoByName(ccEscape(photoname))
        album = photo and photo.album
    else:    
        album = Album.GetAlbumByName(ccEscape(albumname))
        
    if not album:
        return returnerror(translate("Album does not exist"))
    
    if not album.public and not checkAuthorization():
        return returnerror(translate("You are not authorized to access this photo"))
        
    photo = album.GetPhotoByName(ccEscape(photoname))
    if not photo:
        return returnerror(translate("Photo does not exist"))
    
    if request.POST:
        author = ccEscape(request.POST.get("comment_author"))
        content = ccEscape(request.POST.get("comment_content"))
        photo.AddComment(author, content)
        return HttpResponseRedirect((u"/%s/%s"%(albumname,photoname )).encode("utf-8"))
    
    try:    
        current = album.GetPhotoIndex(photo)
    except ValueError:
        current = album.InsertPhoto2List(photo)
        
    total = album.photoCount
    prevphoto = nextphoto = None
    if current > 0:
        prevphoto = Photo.GetPhotoByID(album.photoslist[current-1])
    if current < total-1:
        nextphoto = Photo.GetPhotoByID(album.photoslist[current+1])
    
    content = {"album":album,
               "photo":photo,
               "allalbums":get_all_albums(),
               "prevphoto":prevphoto,"nextphoto":nextphoto,
               "current":current+1,"total":total,
               }
    return render_to_response_with_users_and_settings("photo.html", content)

def search(request):
    try:
        page_index = int(request.GET.get('page',1))
    except:
        page_index = 1
        

    if request.method == "POST":
        searchword = ccEscape(request.POST.get("searchword",""))
        searchmode = ccEscape(request.POST.get("searchmode"))
        save_cookie({"gaephotos-searchword":searchword,
                     "gaephotos-searchmode":searchmode})
        return HttpResponseRedirect('/search/?page=%d'%page_index)
    else:
        searchword = get_cookie("gaephotos-searchword").strip()
        searchmode = get_cookie("gaephotos-searchmode")
        searchmode = searchmode or "album"
    
    public = not checkAuthorization();
    if searchmode == "album":
        if searchword:  
            albums = Album.SearchAlbums(searchword, public)
            entries,pager = CCPager(list=albums,items_per_page=gallery_settings.albums_per_page).fetch(page_index)
        else:
            entries,pager = CCPager(query=get_all_albums(),items_per_page=gallery_settings.albums_per_page).fetch(page_index)
        content = {"albums":entries,
                   "pager": pager,
                   "allalbums":get_all_albums(),
                   "album": {'name':'search', 'id':0,}}
        return render_to_response_with_users_and_settings("index.html", content)
    
    elif searchmode == "photo":
        photos = Photo.SearchPhotos(searchword, public)
            
        entries,pager = CCPager(list=photos,items_per_page=gallery_settings.thumbs_per_page).fetch(page_index)
        content = {"photos":entries,
                   "pager": pager,
                   "allalbums":get_all_albums(),
                   "album": {'name':'search', 'id':0,}}
        return render_to_response_with_users_and_settings("album.html", content)

@pagecache("feed")
def feed(request):
    latestphotos = Photo.GetLatestPhotos(num=gallery_settings.latest_photos_count,
                                          public = True)
                                          
    if latestphotos:
        last_updated = latestphotos[0].updatedate
        last_updated = last_updated.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        last_updated = "1900-01-01T00:00:00Z"
       
    content = {"last_updated": last_updated,
               "latestphotos": latestphotos,
               "gallery_settings": gallery_settings}
    return render_to_atom("atom.xml", content)

@pagecache("showslider")
def showslider(request, albumname):
    album = Album.GetAlbumByName(ccEscape(albumname))
    if album:
        if not album.public and not checkAuthorization():
                return returnerror(translate("You are not authorized"))
 
        photos = album.GetPhotosQuery()
    elif albumname == 'search':
        searchword = get_cookie("gaephotos-searchword","")
        public = not checkAuthorization();
        photos = Photo.SearchPhotos(searchword, public)
        album = {'name':'search', 'id':0,}

    else:
        return returnerror(translate("Album does not exist"))
            
    content = {"album":album,
               "photos":photos,
               "allalbums":get_all_albums(),
               }
    return render_to_response_with_users_and_settings("slider.html", content)

def showimage(request, photoid):
    return showimg(request,photoid, "image")

def showthumb(request, photoid):
    return showimg(request,photoid, "thumb")
    
def showimg(request, photoid, mode="thumb"):
    cache_timeout = 3600*24*30
    try:
        key = "%s_%s"%(mode,long(photoid))
        
        photo = Photo.GetPhotoByID(long(photoid))
        if not photo:
            return returnerror(translate("Photo does not exist"))
        if not photo.isPublic and not checkAuthorization():
                return returnerror(translate("You are not authorized"))
        
        #cachedata = memcache.get(key)
        cachedata = photo.GetCache(mode)
        
        #try to get from cache
        if cachedata and cachedata.get('etag',None):
            if not cachedata['public'] and not checkAuthorization():
                return returnerror(translate("You are not authorized"))
            
            resp = HttpResponse() 
            resp.headers['Date'] = http_date()
            resp.headers['Etag'] = cachedata['etag']
            resp.headers['Cache-Control'] = 'max-age=%d, public' % cache_timeout
            resp.headers['Expires'] = http_date(time.time() + cache_timeout)
            if mode == "thumb":
                resp.headers['Content-Type'] = "image/png"
            else:
                resp.headers['Content-Type'] = cachedata['Content-Type']
                
            if request.environ.get('HTTP_IF_NONE_MATCH') == cachedata['etag']:
                resp.status_code = 304
            else:
                resp.status_code = 200
                resp.write(cachedata['binary'])
            return resp
        
        #no cache
        resp = HttpResponse() 
        if mode == "thumb":
            binary = photo.binary_thumb
            if not binary:
                try:
                    img = images.Image(photo.Binary)
                    img.resize(200, 200)
                    binary = img.execute_transforms()
                except:
                    logging.exception("get thumb error")
                    binary = photo.Binary
            resp.headers['Content-Type'] = "image/png"
        else:
            binary = photo.Binary
            resp.headers['Content-Type'] = photo.contenttype
            
        resp.headers['Date'] = http_date()    
        resp.headers['Etag'] = '"%s"'%(generate_etag(photo.updatedate, 
                                              len(binary),
                                               str(photo.id)))
        resp.headers['Cache-control'] = "max-age=%d,public"%(cache_timeout*365)
        resp.headers['Expires'] = http_date(time.time() + cache_timeout)
        resp.headers['Content-Length'] = len(binary)
        resp.headers['Last-Modified'] = http_date(photo.updatedate)                
        
        resp.write(binary)

        cachedata = {'binary':binary,
                     'public':photo.isPublic,
                     'etag': resp.headers['Etag'],}
        
        if mode == "thumb":
            cachedata.update( {'Content-Type':"image/png"} )
        else:
            cachedata.update( {'Content-Type':photo.contenttype} )
                
        try:
            #memcache.set(key, cachedata, 20*24*3600)
            photo.SetCache(cachedata, mode)
        except:
            logging.exception("memcache set error")
        
        return resp
    
    except Exception,e:
        url = "http://%s/static/images/error.gif"%os.environ["HTTP_HOST"]
        result = urlfetch.fetch(url, deadline=10)
        if result.status_code == 200:
            resp = HttpResponse()
            resp.headers['Content-Type'] = result.headers['Content-Type']
            resp.headers['Cache-control'] = "max-age=%d,public"%(cache_timeout*365)
            resp.write(result.content)
            return resp
        return returnerror(translate("Get photo error"))

def main():
    pass

if __name__ == '__main__':
  main()
  
