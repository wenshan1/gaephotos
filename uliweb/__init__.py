####################################################################
# Author: Limodou@gmail.com
# License: BSD
####################################################################

__author__ = 'limodou'
__author_email__ = 'limodou@gmail.com'
__url__ = 'http://code.google.com/p/uliweb'
__license__ = 'BSD'

import os, sys

application = None
settings = None
urls = []
static_views = []
url_map = None
local = None
apps_dir = 'apps'
use_urls = False
response = None
request = None

workpath = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(workpath, 'lib'))

from uliweb.core.SimpleFrame import (Request, Response, redirect, error, json, 
        POST, GET, post_view, pre_view, url_for, expose, get_app_dir, get_apps
    )