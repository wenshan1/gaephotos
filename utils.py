#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import Cookie
import time
import math

from functools import wraps
from time import gmtime,mktime
from datetime import datetime
from zlib import adler32

from google.appengine.api import users
from google.appengine.api import memcache

from django.shortcuts import render_to_response
from django.utils import simplejson
from django.utils.html import escape
from django.template import loader
from django.http import HttpResponse

from cc_addons.language import translate 
from models import *


def generate_etag(mtime, file_size, real_filename):
    return 'wzsdm-%d-%s-%s' % (
        mktime(mtime.timetuple()),
        file_size,
        adler32(real_filename) & 0xffffffff
    )

def _dump_date(d, delim):
    """Used for `http_date` and `cookie_date`."""
    if d is None:
        d = gmtime()
    elif isinstance(d, datetime):
        d = d.utctimetuple()
    elif isinstance(d, (int, long, float)):
        d = gmtime(d)
    return '%s, %02d%s%s%s%s %02d:%02d:%02d GMT' % (
        ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')[d.tm_wday],
        d.tm_mday, delim,
        ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
         'Oct', 'Nov', 'Dec')[d.tm_mon - 1],
        delim, str(d.tm_year), d.tm_hour, d.tm_min, d.tm_sec
    )

def http_date(timestamp=None):
    """Formats the time to match the RFC1123 date format.

    Accepts a floating point number expressed in seconds since the epoc in, a
    datetime object or a timetuple.  All times in UTC.  The :func:`parse_date`
    function can be used to parse such a date.

    Outputs a string in the format ``Wdy, DD Mon YYYY HH:MM:SS GMT``.

    :param timestamp: If provided that date is used, otherwise the current.
    """
    return _dump_date(timestamp, ' ')
   
def unescape(html):
    return html.replace('&amp;','&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'") 
                                                                                                               
def format_date(dt):
    return dt.strftime('%Y-%m-%d %H:%MGMT')

def ccEscape(str):
    return unicode(escape(str),'utf-8').strip()

def render_to_javasript(*args, **kwargs):
    resp = HttpResponse()
    resp.headers['Content-Type'] = "text/javascript"
    resp.write(loader.render_to_string(*args, **kwargs))
    return resp

def render_to_atom(*args, **kwargs):
    resp = HttpResponse()
    resp.headers['Content-Type'] = "application/atom+xml"
    resp.write(loader.render_to_string(*args, **kwargs))
    return resp
    
# one request one save
def save_cookie(cookie_dict,path="/"):
    cookie = Cookie.SimpleCookie()
    for key in cookie_dict.keys():        
        cookie[key] = simplejson.dumps(cookie_dict[key])
        now = time.asctime()
        cookie[key]['expires'] = now[:-4] + str(int(now[-4:])+1) + ' GMT'
        cookie[key]['path'] = path
        
    print cookie
    
def get_cookie(name,default=None):
    browser_cookie = os.environ.get('HTTP_COOKIE', '')
    cookie = Cookie.SimpleCookie()
    cookie.load(browser_cookie)
    try:
        value = simplejson.loads(cookie[name].value)
    except:
        return default
    
    return value

def Album2Dict(album):
    if not album:
        return {}
    return {"id": album.id,
            "name":album.name,
            "description": unescape(album.description),
            "public":album.public,
            "createdate":format_date(album.createdate),
            "updatedate":format_date(album.updatedate),
            "photoslist":album.photoslist, 
            "coverphotoid": album.coverPhotoID,}
    
def buildComments(comments):
    li = []
    for comment in comments:
        li.append({'author':comment.author, 'content':comment.content,
                   'date':format_date(comment.date), 'id':comment.id,
                   'admin':users.is_current_user_admin(),})
    return li
    
class CCPager(object):

    def __init__(self, model=None,query=None,list=[], items_per_page=8, pages_follow = 5, pages_skip = 10):
        if model:
            self.query = model.all()
        elif query:
            self.query=query
        elif list:
            self.query = None
            self.list = list
        else:
            self.query = None
            self.list = []

        self.items_per_page = items_per_page
        self.pages_follow = pages_follow
        self.pages_skip = pages_skip

    def fetch(self, p):
        if self.query:
            max_offset = self.query.count()
        else:
            max_offset = len(self.list)
            
        n = max_offset / self.items_per_page
        if max_offset % self.items_per_page != 0:
            n += 1

        if p < 0 or p > n:
            p = 1
        offset = (p - 1) * self.items_per_page
        
        if self.query:
            results = self.query.fetch(self.items_per_page, offset)
        else:
            results = self.list[offset:offset+self.items_per_page]



        links = {'count':max_offset,'page_index':p, 
                 'page_count': int(math.ceil(((float)(max_offset))/self.items_per_page)),
                 'prev': p - 1, 'next': p + 1, 'last': n,
                 'follow':range(p+1,n+1),
                 'lead':[],}
        if p > self.pages_skip:
            links['lead'].append(p-self.pages_skip)
        start = 1
        if p-self.pages_follow > start:
            start = p-self.pages_follow
        links['lead'] += range(start,p)
        
        
        if len(links['follow']) > self.pages_follow:
            links['follow'] = links['follow'][:self.pages_follow]
        if links['page_count'] - p > self.pages_skip:
            links['follow'].append(p+self.pages_skip)
        
        if links['next'] > n:
            links['next'] = 0

        return (results, links)

def requires_site_admin(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if not checkAuthorization():
            return returnerror(translate("You are not authorized"))
        else:
            return method(self, *args, **kwargs)
    return wrapper        
        
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
        

def returnerror(msg):
    content = {"error_msg":msg,
               }
    return render_to_response_with_users_and_settings("admin/error.html", content)        
        
def returnjson(dit,response):
    #response.headers['Content-Type'] = "application/json"
    response.write(simplejson.dumps(dit))
    return response 

def render_to_response_with_users_and_settings(templatefile, content):
    global gallery_settings
    if not gallery_settings:
        InitGallery()
    
    gallery_settings.baseurl = "http://"+os.environ["HTTP_HOST"]
    users.is_admin = checkAuthorization()    
    content["users"] = users
    content["gallery_settings"] = gallery_settings
    
    searchword = get_cookie("gaephotos-searchword","")
    searchmode = get_cookie("gaephotos-searchmode")
    content["searchword"] = searchword
    content["searchmode"] = searchmode
    return render_to_response(templatefile, content) 

class ImageMime:
    GIF = "image/gif"
    JPEG = "image/jpeg"
    TIFF = "image/tiff"
    PNG = "image/png"
    BMP = "image/bmp"
    ICO = "image/x-icon"
    UNKNOWN = "application/octet-stream"
    
def getImageType(binary):
    size = len(binary)
    if size >= 6 and binary.startswith("GIF"):
        return ImageMime.GIF
    elif size >= 8 and binary.startswith("\x89PNG\x0D\x0A\x1A\x0A"):
        return ImageMime.PNG
    elif size >= 2 and binary.startswith("\xff\xD8"):
        return ImageMime.JPEG
    elif (size >= 8 and (binary.startswith("II\x2a\x00") or
                         binary.startswith("MM\x00\x2a"))):
        return ImageMime.TIFF
    elif size >= 2 and binary.startswith("BM"):
        return ImageMime.BMP
    elif size >= 4 and binary.startswith("\x00\x00\x01\x00"):
        return ImageMime.ICO
    else:
        return ImageMime.UNKNOWN        
        
def pagecache(method):
    @wraps(method)
    def _wrapper(*args, **kwargs):
        request = args[0]
        if request.POST or request.FILES:
            resp = method(*args, **kwargs)
            return resp
        
        key = "html:" + request.META["PATH_INFO"]+ request.META["QUERY_STRING"]  
        resp = memcache.get(key)
        if resp is not None:
            return resp
        else:
            resp = method(*args, **kwargs)
            if resp.status_code == 200:
                if not memcache.set(key, resp, 60):
                    logging.error("Memcache set failed.")
            return resp
    return _wrapper        

        
        
        