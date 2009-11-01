# -*- coding: utf-8 -*-

import os
import logging
import Cookie
from django.utils import simplejson

from settings import DEFAULT_LANG

COOKIE_NAME = 'gaephotos-language'

def get_current_lang():
    browser_cookie = os.environ.get('HTTP_COOKIE', '')
    cookie = Cookie.SimpleCookie()
    cookie.load(browser_cookie)
    try:
        lang = simplejson.loads(cookie[COOKIE_NAME].value)
    except:
        cookie[COOKIE_NAME] = simplejson.dumps(DEFAULT_LANG)
        print cookie
        lang = DEFAULT_LANG
    return lang

def save_current_lang(lang):
    lang = unicode(lang,'utf-8')
    if not lang_table.has_key(lang):
        lang = DEFAULT_LANG
        
    browser_cookie = os.environ.get('HTTP_COOKIE', '')
    cookie = Cookie.SimpleCookie()
    cookie.load(browser_cookie)
    cookie[COOKIE_NAME] = simplejson.dumps(lang)
    print cookie

def find_msg_index(msg):
    msg = unicode(msg,'utf-8')
    for lang in lang_table.keys():
        index = 0
        for m in lang_table[lang]:
            if m == msg:
                return index
            index += 1

    raise "can not find %s"%msg
        
def translate(msg):
    try:
        return lang_table[get_current_lang()][find_msg_index(msg)]
    except:
        logging.exception('translate error: %s'%msg)
        return msg

lang_table = {
u"en-us":
[
#base.html
u'All Albums',
u'Admin',
u'Logout',
u'Login',
u'Add Photos',
u'Albums Manage',
u'Slide Show',
#index.html
u'private',
#pager.html
u'First Page',
u'Prev Page',
u'Next Page',
u'Last Page',
u'error',
#photo.html
u'Cover Photo Saved',
u'photo description is saving...',
u'posted on',
u'Delete',
u'Pls input content',
u'comment can not over 500 chars',
u'Pls input your name',
u'comment is saving...',
u'Delete this photo',
u'Set as Cover Photo',
u'add description',
u'save',
u'cancel',
u'Prev photo',
u'Next photo',
u'Filename',
u'Owner',
u'Type',
u'Dimensions',
u'Size',
u'Date updated',
u'Web address',
u'click me to post comment(most 500 chars)',
u'name',
u'submit',
#slider.html
u'Play Slideshow',
u'Pause Slideshow',
u'Photo',
#album_manage.html
u'Getting album information...',
u'Saving album settings...',
u'Cleaning album photos...',
u'Deleting album...',
u'Albums List',
u'Create Album',
u'public',
u'Album Description',
u'Album Name',
u'Permission',
u'Cover Photo',
u'Photo Count',
u'Date created',
u'Save Settings',
u'Clean Photos',
u'Delete Album',
u'careful',
u'more careful',
u'R you seriously delete this album?',
u'Are you seriously clean photos of this album?',
u'No, I just try the button',
u'Yes, just delete it',
u'Yes, just clean it',
# settings.html
u'Are you seriously destroy all data?',
u'Data erasing...',
u'Site Title',
u'Site Description',
u'Albums per page',
u'Thumbs per page',
u'Cache Stats',
u'Reset Settings',
u'Clean Caches',
u'Destroy All Data',
u'Caution, photos can not be recovered',
# handlers.js
u'Select Photos',
u'Select Album',
u'Cancel All',
u'Photos Queue',
u'Thumbs',
u'Pending...',
u'Photos are uploading to album',
u'Uploading...',
u'Upload Failed',
u'Photos are uploaded to album ',
# admin.py
u'Room 404, nobody living here',
u'no upload file',
u'no image data',
u'file size exceed 1M',
u'unsupported file type',
u'Album does not exist',
u'Database error',
u'You are not authorized to upload',
u'Photo does not exist',
u'You are not authorized to access this photo',
u'Pls input name and content',
u'You are not authorized',
u'Comment does not exist',
u'Album exist with this name',
u'Get photo error',
u'##Error MSG##',
u'##Error MSG##',
u'##Error MSG##',
u'##Error MSG##',
u'##Error MSG##',
u'##Error MSG##',
u'##Error MSG##',
u'##Error MSG##',
u'##Error MSG##',
u'##Error MSG##',
],

u"zh-cn":
[
u'全部相册',
u'管理',
u'登出',
u'登陆',
u'添加照片',
u'相册管理',
u'查看幻灯片',
u'不公开',
u'最前',
u'上一页',
u'下一页',
u'最后',
u'错误',
u'设置封面成功',
u'正在保存图片说明...',
u'发表于',
u'删除',
u'请输入评论',
u'评论不能多于500字',
u'请输入名字',
u'正在提交评论...',
u'删除照片',
u'设为相册封面',
u'添加说明',
u'保存',
u'取消',
u'上一张',
u'下一张',
u'文件名',
u'添加者',
u'类型',
u'照片尺寸',
u'大小',
u'更新时间',
u'图片网址',
u'点我添加评论(最多500字)',
u'名字',
u'提交',
u'自动播放',
u'暂停播放',
u'照片',
u'正在获取相册信息...',
u'正在保存相册设置...',
u'正在清空图片...',
u'正在删除相册...',
u'相册列表',
u'新建相册',
u'公开',
u'相册简介',
u'相册名字',
u'权限设置',
u'相册封面',
u'照片数量',
u'创建时间',
u'保存设置',
u'清空图片',
u'删除相册',
u'慎重',
u'慎慎重',
u'你真的要删除相册?',
u'你真的要清空相册图片?',
u'No,不小心点错了',
u'是的,我要删除相册',
u'是的,我要清空图片',
u'你真的要清空所有数据?',
u'正在清空数据...',
u'网站标题',
u'网站说明',
u'每页显示的相册数',
u'每页显示的图片数',
u'缓存状态',
u'恢复默认设置',
u'清空图片缓存',
u'清空所有数据',
u'请慎重,所有图片将被删除',
u'选择相片上传',
u'请选择相册先',
u'全部取消',
u'上传图片队列',
u'缩略图',
u'等待ing...',
u'正在上传照片到相册',
u'上传ing...',
u'上传错误',
u'张照片已经上传到相册',
# admin.py
u'404 查无此人,地址不存在',
u'没有文件',
u'没有图片数据',
u'文件大小超过 1M 限制',
u'不支持的文件格式',
u'找不到相册',
u'数据库错误',
u'你没有上传权限',
u'照片不存在',
u'你没有权限访问这张照片',
u'请填写名字和评论内容',
u'你没有权限',
u'没有这条评论',
u'同名的相册已存在',
u'获取相片出错',
u'##出错了##',
u'##出错了##',
u'##出错了##',
u'##出错了##',
u'##出错了##',
u'##出错了##',
u'##出错了##',
u'##出错了##',
u'##出错了##',
u'##出错了##',
u'##出错了##',
],              
              
}



