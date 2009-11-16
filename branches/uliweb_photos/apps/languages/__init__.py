# -*- coding: utf-8 -*-

import os
import logging
import Cookie
import time

from uliweb.core.dispatch import bind
import simplejson


COOKIE_NAME = 'gaephotos-language'
DEFAULT_LANG = 'en-us'

@bind('startup_installed')
def startup(sender):
    global DEFAULT_LANG
    DEFAULT_LANG = sender.settings.GLOBAL.DEFAULT_LANG

def get_current_lang():
    browser_cookie = os.environ.get('HTTP_COOKIE', '')
    cookie = Cookie.SimpleCookie()
    cookie.load(browser_cookie)
    try:
        lang = simplejson.loads(cookie[COOKIE_NAME].value)
    except:
        save_current_lang(DEFAULT_LANG)
        lang = DEFAULT_LANG
    return lang

def save_current_lang(lang):
    if type(lang) != unicode:
        lang = unicode(lang,'utf-8')
    
    if not lang_table.has_key(lang):
        lang = DEFAULT_LANG
        
    cookie = Cookie.SimpleCookie()
    now = time.asctime()
    cookie[COOKIE_NAME] = simplejson.dumps(lang)
    cookie[COOKIE_NAME]['expires'] = now[:-4] + str(int(now[-4:])+1) + ' GMT'
    cookie[COOKIE_NAME]['path'] = '/'
    print cookie

def find_msg_index(msg):
    if type(msg) != unicode:
        msg = unicode(msg,'utf-8')
    for lang in lang_table.keys():
        index = 0
        for m in lang_table[lang]:
            if unicode(m, 'utf-8') == msg:
                return index
            index += 1

    raise "can not find %s"%str(msg)
        
def translate(msg):
    try:
        return lang_table[get_current_lang()][find_msg_index(msg)]
    except:
        logging.exception('translate error: %s'%msg)
        return msg

_ = translate

@bind('prepare_default_env')
def prepare_default_env(sender, env):
    env['translate'] = translate
    env['_'] = translate
    
lang_table = {
u"en-us":
[
'Album',
'Photo',
#base.html
'All Albums',
'Admin',
'Logout',
'Login',
'Add Photos',
'Albums Manage',
'Slide Show',
#index.html
'private',
#pager.html
'First Page',
'Prev Page',
'Next Page',
'Last Page',
'error',
#photo.html
'Cover Photo Saved',
'photo description is saving...',
'posted on',
'Delete',
'Pls input content',
'comment can not over 500 chars',
'Pls input your name',
'comment is saving...',
'Delete this photo',
'Set as Cover Photo',
'add description',
'save',
'cancel',
'Prev photo',
'Next photo',
'Filename',
'Owner',
'Type',
'Dimensions',
'Size',
'Date updated',
'Web address',
'click me to post comment(most 500 chars)',
'name',
'submit',
#slider.html
'Play Slideshow',
'Pause Slideshow',
'Photo',
#album_manage.html
'Getting album information...',
'Saving album settings...',
'Cleaning album photos...',
'Deleting album...',
'Albums List',
'Create Album',
'public',
'Album Description',
'Album Name',
'Permission',
'Cover Photo',
'Photo Count',
'Date created',
'Save Settings',
'Clean Photos',
'Delete Album',
'careful',
'more careful',
'R you seriously delete this album?',
'Are you seriously clean photos of this album?',
'No, I just try the button',
'Yes, just delete it',
'Yes, just clean it',
# settings.html
'Are you seriously destroy all data?',
'Data erasing...',
'Site Title',
'Site Description',
'Albums per page',
'Thumbs per page',
'Cache Stats',
'Reset Settings',
'Clean Caches',
'Destroy All Data',
'Caution, photos can not be recovered',
# handlers.js
'Select Photos',
'Select Album',
'Cancel All',
'Photos Queue',
'Thumbs',
'Pending...',
'Photos are uploading to album',
'Uploading...',
'Upload Failed',
'Photos are uploaded to album',
# admin.py
'Room 404, nobody living here',
'no upload file',
'no image data',
'file size exceed 1M',
'unsupported file type',
'Album does not exist',
'Database error',
'You are not authorized to upload',
'Photo does not exist',
'You are not authorized to access this photo',
'Pls input name and content',
'You are not authorized',
'Comment does not exist',
'Album exist with this name',
'Get photo error',
'filename can not contain space',
'Admins',
'no album found',
'Search',
'no photo found',
'Latest Comments',
'Latest Photos',
'Latest Photos Count',
'Latest Comments Count',
'##Error MSG##',
],

u"zh-cn":
[
'相册',
'照片',
'全部相册',
'管理',
'登出',
'登陆',
'添加照片',
'相册管理',
'查看幻灯片',
'不公开',
'最前',
'上一页',
'下一页',
'最后',
'错误',
'设置封面成功',
'正在保存图片说明...',
'发表于',
'删除',
'请输入评论',
'评论不能多于500字',
'请输入名字',
'正在提交评论...',
'删除照片',
'设为相册封面',
'添加说明',
'保存',
'取消',
'上一张',
'下一张',
'文件名',
'添加者',
'类型',
'照片尺寸',
'大小',
'更新时间',
'图片网址',
'点我添加评论(最多500字)',
'名字',
'提交',
'自动播放',
'暂停播放',
'照片',
'正在获取相册信息...',
'正在保存相册设置...',
'正在清空图片...',
'正在删除相册...',
'相册列表',
'新建相册',
'公开',
'相册简介',
'相册名字',
'权限设置',
'相册封面',
'照片数量',
'创建时间',
'保存设置',
'清空图片',
'删除相册',
'慎重',
'慎慎重',
'你真的要删除相册?',
'你真的要清空相册图片?',
'No,不小心点错了',
'是的,我要删除相册',
'是的,我要清空图片',
'你真的要清空所有数据?',
'正在清空数据...',
'网站标题',
'网站说明',
'每页显示的相册数',
'每页显示的图片数',
'缓存状态',
'恢复默认设置',
'清空图片缓存',
'清空所有数据',
'请慎重,所有图片将被删除',
'选择相片上传',
'请选择相册先',
'全部取消',
'上传图片队列',
'缩略图',
'等待ing...',
'正在上传照片到相册',
'上传ing...',
'上传错误',
'张照片已经上传到相册',
# admin.py
'404 查无此人,地址不存在',
'没有文件',
'没有图片数据',
'文件大小超过 1M 限制',
'不支持的文件格式',
'找不到相册',
'数据库错误',
'你没有上传权限',
'照片不存在',
'你没有权限访问这张照片',
'请填写名字和评论内容',
'你没有权限',
'没有这条评论',
'同名的相册已存在',
'获取相片出错',
'文件名不能包含空白字符',
'管理员',
'没有任何相册',
'搜索',
'没有任何照片',
'最新评论',
'最新照片',
'显示的最新照片数',
'显示的最新评论数',
'##出错了##',
'##出错了##',
],              
              
}