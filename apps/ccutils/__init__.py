# -*- coding: utf-8 -*-
import os
import re
import math
import cgi
import Cookie
import simplejson
import time

from werkzeug.utils import http_date

def ccGetcookie(name,default=None):
    browser_cookie = os.environ.get('HTTP_COOKIE', '')
    cookie = Cookie.SimpleCookie()
    cookie.load(browser_cookie)
    try:
        value = simplejson.loads(cookie[name].value)
    except:
        return default
    
    return value

def ccSavecookie(cookie_dict, timeout=0, path="/"):
    cookie = Cookie.SimpleCookie()
    for key in cookie_dict.keys():        
        cookie[key] = simplejson.dumps(cookie_dict[key])
        now = time.asctime()
        cookie[key]['expires'] = http_date(time.time() + timeout)#now[:-4] + str(int(now[-4:])+1) + ' GMT'
        cookie[key]['path'] = path
        
    print cookie
    
def ccEscape(str):
    if type(str) == unicode:
        return str.strip()
    return unicode(cgi.escape(str),'utf-8').strip()  

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