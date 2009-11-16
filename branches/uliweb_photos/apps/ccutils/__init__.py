# -*- coding: utf-8 -*-
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
# Purpose: some utils.
# Created: 11/15/2009
#===============================================================================

import os
import re
import cgi
import time
import math
import Cookie
import simplejson

from time import gmtime
from datetime import datetime

# from werkzeug.utils
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
    
def ccEscape(str):
    if type(str) == unicode:
        str = str.encode('utf-8')
    return unicode(cgi.escape(str),'utf-8').strip()  

def ccUnEscape(html):
    if type(html) == unicode:
        html = html.encode('utf-8')
    return html.replace('&amp;','&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'") 
                                                                                                               
def ccFormatDate(dt):
    return dt.strftime('%Y-%m-%d %H:%M GMT')

def ccGetCookie(name,default=None):
    browser_cookie = os.environ.get('HTTP_COOKIE', '')
    cookie = Cookie.SimpleCookie()
    cookie.load(browser_cookie)
    try:
        value = simplejson.loads(cookie[name].value)
    except:
        return default
    
    return value

def ccSaveCookie(cookie_dict, timeout=0, path="/"):
    cookie = Cookie.SimpleCookie()
    for key in cookie_dict.keys():        
        cookie[key] = simplejson.dumps(cookie_dict[key])
        now = time.asctime()
        cookie[key]['expires'] = _dump_date(time.time() + timeout, '-')#now[:-4] + str(int(now[-4:])+1) + ' GMT'
        cookie[key]['path'] = path
        
    print cookie

class ccDict(dict):        
    def __getattr__(self, name):
        return self[name]
    
    def __setattr__(self, name, value):
        self[name] = value
        
    def __delattr__(self, key):
        del self[key]
        
    def __getstate__(self): 
        return dict(self)
    
    def __setstate__(self,values):
        for k,v in values.items(): 
            self[k]=v

def ccTruncateWords(string, length=20):
    words = string.split()
    if len(words) > length:
        words = words[:length]
        if not words[-1].endswith('...'):
            words.append('...')
    return ' '.join(words)

def ccTruncateCnWords(string, length=20):
    try:
        words = string.decode('ascii')
        return ccTruncateWords(string, length)
    except:
        pass
    words = string
    if len(words) > length:
        words = words[:length]
        if not words[-1].endswith('...'):
            words += ('...')
    return words  

def ccBreakLines(string):
    string = re.sub(r'\r\n|\r|\n', '\n', string)
    lines = re.split('\n{2,}', string)
    lines = ['<p>%s</p>' % l.strip().replace('\n', '<br />') for l in lines]
    return '\n\n'.join(lines)  

class ccPager(object):
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


        links = ccDict({'count':max_offset,'page_index':p, 
                 'page_count': int(math.ceil(((float)(max_offset))/self.items_per_page)),
                 'prev': p - 1, 'next': p + 1, 'last': n,
                 'follow':range(p+1,n+1),
                 'lead':[],})
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
    