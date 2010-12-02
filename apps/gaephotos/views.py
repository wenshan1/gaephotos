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
# Purpose: user views for GAEPhotos
# Created: 11/15/2009
#===============================================================================

import time
import logging

from google.appengine.api import users
from google.appengine.api import images
from google.appengine.api import memcache
from google.appengine.api import urlfetch

from uliweb import expose
from uliweb.core.dispatch import bind
from uliweb.core.SimpleFrame import Response
from uliweb.utils.filedown import _generate_etag
from werkzeug.utils import http_date

from models import *
from ccutils import *
from comm import *
from languages import translate,save_current_lang


@bind('prepare_default_env')
def prepare_default_env(sender, env):
    import ccutils
    
    global gallery_settings
    if not gallery_settings:
        gallery_settings = InitGallery()
    env['gallery_settings'] = gallery_settings
    users.is_admin = checkAuthorization
    env['users'] = users
    env['ccutils'] = ccutils
    
@bind('before_render_template')
def before_render_template(sender, vars, env):
    searchword = ccGetCookie("gaephotos-searchword","")
    searchmode = ccGetCookie("gaephotos-searchmode","")
    env["searchword"] = searchword.encode('utf-8')
    env["searchmode"] = searchmode.encode('utf-8')

    
@expose('/login/')
def login():
    return redirect(users.create_login_url(request.referrer or "/"))

@expose('/logout/')    
def logout():
    return redirect(users.create_logout_url(request.referrer or "/"))    
    

@expose('/')
def index():
    lang = request.GET.get("lang")
    if lang:
        save_current_lang(lang)
        return redirect(request.referrer or "/")
    
    try:
        page_index = int(request.GET["page"])
    except:
        page_index = 1
    
    if checkAuthorization():
        try:
            albums = Album.all().order("-updatedate")
            entries,pager = ccPager(query=albums,items_per_page=gallery_settings.albums_per_page).fetch(page_index)
        except:
            albums = Album.all()
            entries,pager = ccPager(query=albums,items_per_page=gallery_settings.albums_per_page).fetch(page_index)
    else:
        try:
            albums = Album.GetPublicAlbums().order("-updatedate")
            entries,pager = ccPager(query=albums,items_per_page=gallery_settings.albums_per_page).fetch(page_index)
        except:
            albums = Album.GetPublicAlbums()
            entries,pager = ccPager(query=albums,items_per_page=gallery_settings.albums_per_page).fetch(page_index)
    
    try:
        latestcomments = Comment.all().order("-date").fetch(gallery_settings.latest_comments_count)    
    except:
        latestcomments = Comment.all().fetch(gallery_settings.latest_comments_count)   
        
    latestphotos = Photo.GetLatestPhotos(num=gallery_settings.latest_photos_count,
                                          showprivate= checkAuthorization())
        
    content = {"albums":entries,
               "pager": pager,
               "latestcomments": latestcomments,
               "latestphotos": latestphotos}    
            
    return content

@expose('/feed')
def feed():
    latestphotos = Photo.GetLatestPhotos(num=gallery_settings.latest_photos_count,
                                          showprivate= checkAuthorization())
                                          
    if latestphotos:
       last_updated = latestphotos[0].updatedate
       last_updated = last_updated.strftime("%Y-%m-%dT%H:%M:%SZ")
       
    content = {"last_updated": last_updated,
               "latestphotos": latestphotos,
               "gallery_settings": gallery_settings}
    return render_to_atom("atom.xml", content)

@expose('/<albumname>/')
def album(albumname):
    try:
        page_index = int(request.GET['page'])
    except:
        page_index = 1
        
    album = Album.GetAlbumByName(ccEscape(albumname))
    if album:
        if not album.public and not checkAuthorization():
                return returnerror(translate("You are not authorized"))

        if checkAuthorization():
            try:
                albums = Album.all().order("-updatedate")
            except:
                albums = Album.all()
        else:
            try:
                albums = Album.GetPublicAlbums().order("-updatedate")
            except:
                albums = Album.GetPublicAlbums()

        try:    
            photos = album.GetPhotos()
            entries,pager = ccPager(query=photos,items_per_page=gallery_settings.thumbs_per_page).fetch(page_index)
        except:
            photos = Photo.all().filter("album =", album)
            entries,pager = ccPager(query=photos,items_per_page=gallery_settings.thumbs_per_page).fetch(page_index)
    else:
        return returnerror(translate("Album does not exist"))
            
    content = {"album":album,
               "albums":albums,
               "photos":entries,
               "pager": pager}
    
    return content

@expose('/<albumname>/<photoname>')
def photo(albumname, photoname):
    if albumname=="search":
        photo = Photo.GetPhotoByName(ccEscape(photoname))
        album = photo and photo.album
    else:    
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
        return redirect((u"/%s/%s"%(albumname,photoname )).encode("utf-8"))
        
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
    
    if checkAuthorization():
        try:
            albums = Album.all().order("-updatedate")
        except:
            albums = Album.all()
    else:
        try:
            albums = Album.GetPublicAlbums().order("-updatedate")
        except:
            albums = Album.GetPublicAlbums()

    content = {"album":album,
               "albums":albums,
               "photo":photo,
               "prevphoto":prevphoto,"nextphoto":nextphoto,
               "current":current+1,"total":total,}
    return content

@expose('/search/')
def search():
    try:
        page_index = int(request.GET.get('page',1))
    except:
        page_index = 1
        

    if request.POST:
        searchword = ccEscape(request.POST.get("searchword",""))
        searchmode = ccEscape(request.POST.get("searchmode"))
        ccSaveCookie({"gaephotos-searchword":searchword,
                     "gaephotos-searchmode":searchmode}, timeout=3600*24*365)
        return redirect('/search/?page=%d'%page_index)
    else:
        searchword = ccGetCookie("gaephotos-searchword")
        searchmode = ccGetCookie("gaephotos-searchmode")
        searchmode = searchmode or "album"
    
  
    if searchmode == "album":
        albums = Album.SearchAlbums(searchword)
        if not checkAuthorization():
            albums = [album for album in albums if album.public]
            
        entries,pager = ccPager(list=albums,items_per_page=gallery_settings.albums_per_page).fetch(page_index)
        content = {"albums":entries,
               "pager": pager,
               "album": ccDict({'name':'search'})}
        response.template = "index.html"
        return content
    
    elif searchmode == "photo":
        photos = Photo.SearchPhotos(searchword)
        if not checkAuthorization():
            photos = [photo for photo in photos if photo.album.public]
            
        entries,pager = ccPager(list=photos,items_per_page=gallery_settings.thumbs_per_page).fetch(page_index)
        content = {"photos":entries,
               "pager": pager,
               "album": ccDict({'name':'search'})}
        response.template = "album.html"
        return content

@expose('/showslider/<albumname>/')
def slider(albumname):
    album = Album.GetAlbumByName(ccEscape(albumname))
    if album:
        if not album.public and not checkAuthorization():
                return returnerror(translate("You are not authorized"))
        try:    
            photos = album.GetPhotos()
        except:
            photos = album.GetPhotos("")
    elif albumname == 'search':
        searchword = ccGetCookie("gaephotos-searchword","")
        photos = Photo.SearchPhotos(searchword)
        if not checkAuthorization():
            photos = [photo for photo in photos if photo.album.public]
        album = ccDict({'name':'search'})

    else:
        return returnerror(translate("Album does not exist"))
            
    content = {"album":album,
               "photos":photos,
               }
    return content


@expose('/showimage/<photoid>/')
def showimage(photoid):
    return showimg(photoid, "image")
#    cache_timeout = 3600*24*30
#    try:
#        key = "image_%s"%(long(photoid))
#        cachedata = memcache.get(key)
#        
#        if cachedata and cachedata.get('etag',None):
#            if not cachedata['public'] and not checkAuthorization():
#                return returnerror(translate("You are not authorized"))
#            
#            headers = [
#                ('Date', http_date()),
#                ('Content-Type', cachedata['Content-Type']),
#                ('Etag', cachedata['etag']),
#                ('Cache-Control', 'max-age=%d, public' % cache_timeout),
#                ('Expires', http_date(time.time() + cache_timeout)),
#            ]
#            if request.environ.get('HTTP_IF_NONE_MATCH') == cachedata['etag']:
#                resp = Response(status=304, headers=headers)
#            else:
#                resp = Response(status=200, headers=headers)
#                resp.write(cachedata['binary'])
#            return resp
#        
#        #no cache
#        photo = Photo.GetPhotoByID(long(photoid))
#        if not photo.album.public and not checkAuthorization():
#                return returnerror(translate("You are not authorized"))
#            
#        binary = photo.binary
#        
#        resp = Response()
#        resp.headers['Content-Type'] = photo.contenttype
#        resp.headers['Date'] = http_date()    
#        resp.headers['Etag'] = '"%s"'%(_generate_etag(photo.updatedate, 
#                                              len(binary),
#                                               str(photo.id)))
#        resp.headers['Cache-control'] = "max-age=%d,public"%(cache_timeout*365)
#        resp.headers['Expires'] = http_date(time.time() + cache_timeout)
#        resp.headers['Content-Length'] = len(binary)
#        resp.headers['Last-Modified'] = http_date(photo.updatedate)                
#        
#        resp.write(binary)
#
#        cachedata = {'binary':binary,
#                     'public':photo.album.public,
#                     'etag': resp.headers['Etag'],
#                     'Content-Type':photo.contenttype,}
#        try:
#            memcache.set(key, cachedata, 20*24*3600)
#        except:
#            pass
#        
#        return resp
#    except:
#        url = "http://%s/static/images/error.gif"%os.environ["HTTP_HOST"]
#        result = urlfetch.fetch(url, deadline=10)
#        if result.status_code == 200:
#            resp = Response()
#            resp.headers['Content-Type'] = result.headers['Content-Type']
#            resp.headers['Cache-control'] = "max-age=%d"%(3600*24*30*365)
#            resp.write(result.content)
#            return resp
#        return returnerror(translate("Get photo error"))
    
@expose('/thumb/<photoid>.png')
def showthumb(photoid):
    return showimg(photoid, "thumb")
#    cache_timeout = 3600*24*30
#    try:
#        key = "thumb_%s"%(long(photoid))
#        cachedata = memcache.get(key)
#        
#        if cachedata and cachedata.get('etag',None):
#            if not cachedata['public'] and not checkAuthorization():
#                return returnerror(translate("You are not authorized"))
#            
#            headers = [
#                ('Date', http_date()),
#                ('Content-Type', "image/png"),
#                ('Etag', cachedata['etag']),
#                ('Cache-Control', 'max-age=%d, public' % cache_timeout),
#                ('Expires', http_date(time.time() + cache_timeout)),
#            ]
#            if request.environ.get('HTTP_IF_NONE_MATCH') == cachedata['etag']:
#                resp = Response(status=304, headers=headers)
#            else:
#                resp = Response(status=200, headers=headers)
#                resp.write(cachedata['binary'])
#            return resp
#        
#        #no cache
#        photo = Photo.GetPhotoByID(long(photoid))
#        if not photo.album.public and not checkAuthorization():
#                return returnerror(translate("You are not authorized"))
#            
#        binary_thumb = photo.binary_thumb
#        if not binary_thumb:
#            img = images.Image(photo.binary)
#            img.resize(200, 200)
#            binary_thumb = img.execute_transforms()
#        
#        resp = Response()
#        resp.headers['Content-Type'] = "image/png"
#        resp.headers['Date'] = http_date()    
#        resp.headers['Etag'] = '"%s"'%(_generate_etag(photo.updatedate, 
#                                              len(binary_thumb),
#                                               str(photo.id)))
#        resp.headers['Cache-control'] = "max-age=%d,public"%(cache_timeout*365)
#        resp.headers['Expires'] = http_date(time.time() + cache_timeout)
#        resp.headers['Content-Length'] = len(binary_thumb)
#        resp.headers['Last-Modified'] = http_date(photo.updatedate)                
#        
#        resp.write(binary_thumb)
#
#        cachedata = {'binary':binary_thumb,
#                     'public':photo.album.public,
#                     'etag': resp.headers['Etag'],}
#        memcache.set(key, cachedata, 20*24*3600)
#        
#        return resp
#    except:
#        url = "http://%s/static/images/error.gif"%os.environ["HTTP_HOST"]
#        result = urlfetch.fetch(url, deadline=10)
#        if result.status_code == 200:
#            resp = Response()
#            resp.headers['Content-Type'] = result.headers['Content-Type']
#            resp.headers['Cache-control'] = "max-age=%d"%(3600*24*30*365)
#            resp.write(result.content)
#            return resp
#        return returnerror(translate("Get photo error"))

def showimg(photoid, mode="thumb"):
    cache_timeout = 3600*24*30
    try:
        key = "%s_%s"%(mode,long(photoid))
        cachedata = memcache.get(key)
        
        if cachedata and cachedata.get('etag',None):
            if not cachedata['public'] and not checkAuthorization():
                return returnerror(translate("You are not authorized"))
            
            headers = [
                ('Date', http_date()),
                ('Etag', cachedata['etag']),
                ('Cache-Control', 'max-age=%d, public' % cache_timeout),
                ('Expires', http_date(time.time() + cache_timeout)),
            ]
            if mode == "thumb":
                headers.append( ('Content-Type', "image/png") )
            else:
                headers.append( ('Content-Type', cachedata['Content-Type']) )
                
            if request.environ.get('HTTP_IF_NONE_MATCH') == cachedata['etag']:
                resp = Response(status=304, headers=headers)
            else:
                resp = Response(status=200, headers=headers)
                resp.write(cachedata['binary'])
            return resp
        
        #no cache
        photo = Photo.GetPhotoByID(long(photoid))
        if not photo.album.public and not checkAuthorization():
                return returnerror(translate("You are not authorized"))
            
        
        resp = Response() 
        if mode == "thumb":
            binary = photo.binary_thumb
            if not binary:
                img = images.Image(photo.binary)
                img.resize(200, 200)
                binary = img.execute_transforms()
            resp.headers['Content-Type'] = "image/png"
        else:
            binary = photo.binary
            resp.headers['Content-Type'] = photo.contenttype
            
        resp.headers['Date'] = http_date()    
        resp.headers['Etag'] = '"%s"'%(_generate_etag(photo.updatedate, 
                                              len(binary),
                                               str(photo.id)))
        resp.headers['Cache-control'] = "max-age=%d,public"%(cache_timeout*365)
        resp.headers['Expires'] = http_date(time.time() + cache_timeout)
        resp.headers['Content-Length'] = len(binary)
        resp.headers['Last-Modified'] = http_date(photo.updatedate)                
        
        resp.write(binary)

        cachedata = {'binary':binary,
                     'public':photo.album.public,
                     'etag': resp.headers['Etag'],}
        
        if mode == "thumb":
            cachedata.update( {'Content-Type':"image/png"} )
        else:
            cachedata.update( {'Content-Type':photo.contenttype} )
                
        try:
            memcache.set(key, cachedata, 20*24*3600)
        except:
            logging.exception("memcache set error")
        
        return resp
    
    except:
        url = "http://%s/static/images/error.gif"%os.environ["HTTP_HOST"]
        result = urlfetch.fetch(url, deadline=10)
        if result.status_code == 200:
            resp = Response()
            resp.headers['Content-Type'] = result.headers['Content-Type']
            resp.headers['Cache-control'] = "max-age=%d"%(3600*24*30*365)
            resp.write(result.content)
            return resp
        return returnerror(translate("Get photo error"))
