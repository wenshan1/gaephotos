#coding=utf-8
import logging
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


@bind('prepare_default_env')
def prepare_default_env(sender, env):
    global gallery_settings
    if not gallery_settings:
        gallery_settings = InitGallery()
    env['gallery_settings'] = gallery_settings
    users.is_admin = checkAuthorization
    env['users'] = users
    env['ccutils'] = ccutils
    
@bind('before_render_template')
def before_render_template(sender, vars, env):
    searchword = ccGetcookie("gaephotos-searchword","")
    searchmode = ccGetcookie("gaephotos-searchmode","")
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
        
    try:
        latestphotos = Photo.all().order("-updatedate").fetch(gallery_settings.latest_photos_count) 
    except:
        latestphotos = Photo.all().fetch(gallery_settings.latest_photos_count) 
        
    content = {"albums":entries,
               "pager": pager,
               "latestcomments": latestcomments,
               "latestphotos": latestphotos}    
            
    return content

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
        
        try:    
            photos = album.GetPhotos()
            entries,pager = ccPager(query=photos,items_per_page=gallery_settings.thumbs_per_page).fetch(page_index)
        except:
            photos = Photo.all().filter("album =", album)
            entries,pager = ccPager(query=photos,items_per_page=gallery_settings.thumbs_per_page).fetch(page_index)
    else:
        return returnerror(translate("Album does not exist"))
            
    content = {"album":album,
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
    
    content = {"album":album,
               "photo":photo,
               "prevphoto":prevphoto,"nextphoto":nextphoto,
               "current":current+1,"total":total,
               }
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
        ccSavecookie({"gaephotos-searchword":searchword,
                     "gaephotos-searchmode":searchmode}, timeout=3600*24*365)
        return redirect('/search/?page=%d'%page_index)
    else:
        searchword = ccGetcookie("gaephotos-searchword")
        searchmode = ccGetcookie("gaephotos-searchmode")
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
        searchword = ccGetcookie("gaephotos-searchword","")
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
        cache_timeout = 3600*24*30
#    try:
        key = "image_%s"%(long(photoid))
        cachedata = memcache.get(key)
        
        if cachedata and cachedata.get('etag',None):
            if not cachedata['public'] and not checkAuthorization():
                return returnerror(translate("You are not authorized"))
            
            headers = [
                ('Date', http_date()),
                ('Content-Type', cachedata['Content-Type']),
                ('Etag', cachedata['etag']),
                ('Cache-Control', 'max-age=%d, public' % cache_timeout),
                ('Expires', http_date(time.time() + cache_timeout)),
            ]
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
            
        binary = photo.binary
        
        resp = Response()
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
                     'etag': resp.headers['Etag'],
                     'Content-Type':photo.contenttype,}
        try:
            memcache.set(key, cachedata, 20*24*3600)
        except:
            pass
        
        return resp
#    except:
#        url = "http://%s/static/images/error.gif"%os.environ["HTTP_HOST"]
#        result = urlfetch.fetch(url, deadline=10)
#        if result.status_code == 200:
#            resp.headers['Content-Type'] = result.headers['Content-Type']
#            resp.headers['Cache-control'] = "max-age=%d"%(3600*24*30*365)
#            resp.write(result.content)
#            return resp
#        return returnerror(translate("Get photo error"))
    
@expose('/thumb/<photoid>.png')
def showthumb(photoid):
        cache_timeout = 3600*24*30
#    try:
        key = "thumb_%s"%(long(photoid))
        cachedata = memcache.get(key)
        
        if cachedata and cachedata.get('etag',None):
            if not cachedata['public'] and not checkAuthorization():
                return returnerror(translate("You are not authorized"))
            
            headers = [
                ('Date', http_date()),
                ('Content-Type', "image/png"),
                ('Etag', cachedata['etag']),
                ('Cache-Control', 'max-age=%d, public' % cache_timeout),
                ('Expires', http_date(time.time() + cache_timeout)),
            ]
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
            
        binary_thumb = photo.binary_thumb
        if not binary_thumb:
            img = images.Image(photo.binary)
            img.resize(200, 200)
            binary_thumb = img.execute_transforms()
        
        resp = Response()
        resp.headers['Content-Type'] = "image/png"
        resp.headers['Date'] = http_date()    
        resp.headers['Etag'] = '"%s"'%(_generate_etag(photo.updatedate, 
                                              len(binary_thumb),
                                               str(photo.id)))
        resp.headers['Cache-control'] = "max-age=%d,public"%(cache_timeout*365)
        resp.headers['Expires'] = http_date(time.time() + cache_timeout)
        resp.headers['Content-Length'] = len(binary_thumb)
        resp.headers['Last-Modified'] = http_date(photo.updatedate)                
        
        resp.write(binary_thumb)

        cachedata = {'binary':binary_thumb,
                     'public':photo.album.public,
                     'etag': resp.headers['Etag'],}
        memcache.set(key, cachedata, 20*24*3600)
        
        return resp
#    except:
#        url = "http://%s/static/images/error.gif"%os.environ["HTTP_HOST"]
#        result = urlfetch.fetch(url, deadline=10)
#        if result.status_code == 200:
#            resp.headers['Content-Type'] = result.headers['Content-Type']
#            resp.headers['Cache-control'] = "max-age=%d"%(3600*24*30*365)
#            resp.write(result.content)
#            return resp
#        return returnerror(translate("Get photo error"))



#=======================================================================
# Admin views 
#=======================================================================
@requires_site_admin
@expose('/admin/album/')
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

@expose('/admin/ajaxaction/')
def ajaxAction():
    try:
        resp = Response()
        
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
                logging.info( buildcomments(photo.GetComments()) )
                return returnjson({"result":"ok",
                         "comments": buildcomments(photo.GetComments())}, resp)
        
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
                                   "album":album2dict(album),
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
                                   "album":album2dict(album),
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
                                   "album":album2dict(album),
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
                                   "album":album2dict(album),
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
                         "comments": buildcomments(photo.GetComments())}, resp)
            else:
                return returnjson({"result":"error",
                                   "msg":ccEscape(translate("Comment does not exist"))}, resp)
            
        return returnjson({"result":"error",
                           "msg":ccEscape("no action")}, resp)
    except Exception,e:
        return returnjson({"result":"error",
                           "msg":str(e)}, resp)

