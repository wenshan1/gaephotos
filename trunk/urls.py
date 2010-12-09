from django.conf.urls.defaults import *

urlpatterns = patterns('views',
    (r'^$', 'index'),
    (r'^search/$', 'search'),
    (r'^feed/$', 'feed'),
    (r'^showalbum/(?P<albumname>[\S\s]+?)/$', ''),
    (r'^thumb/(?P<photoid>[\S]+?)\.png$', 'showthumb'),
    (r'^showimage/(?P<photoid>[\S]+?)/$', 'showimage'),
    (r'^showslider/(?P<albumname>[\S\s]+?)/$', 'showslider'),
)

urlpatterns += patterns('admin',
    (r'^localjavascript/(?P<scriptname>[\S]+?).js','localjavascript'),
    (r'^login/$', 'login'),
    (r'^logout/$', 'logout'),
    (r'^admin/uploadphoto/$', 'swfuploadphoto'),
    (r'^admin/uploadv2/$', 'uploadv2'),
    (r'^admin/delphoto/(?P<photoid>[\S]+?)/$', 'delphoto'),
    (r'^admin/settings/$', 'settings'),
    (r'^admin/album/$', 'albummanage'),
    (r'^admin/ajaxaction/$', 'ajaxAction'),
    (r'^admin/[\S\s]+?/{0,1}$', 'adminerror'),
)

urlpatterns += patterns('views',
    (r'^(?P<albumname>[\S\s]+?)/(?P<photoname>[\S\s]+?)/$', 'photo'),
    (r'^(?P<albumname>[\S\s]+?)/(?P<photoname>[\S\s]+?)$', 'photo'),
    (r'^(?P<albumname>[\S\s]+?)/$', 'album'),
)