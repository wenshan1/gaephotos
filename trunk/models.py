# -*- coding: utf-8 -*-
import os
import logging
from datetime import datetime

from google.appengine.ext import db
from google.appengine.api import datastore
from google.appengine.api import datastore_errors
from google.appengine.api import users


class GallerySettings(db.Model):
    #domain = db.StringProperty(multiline=False)
    #baseurl = db.StringProperty(multiline=False,default=None)
    title = db.StringProperty(default="GAE Photos")
    owner = db.UserProperty()
    description = db.StringProperty(multiline=True)
    albums_per_page = db.IntegerProperty(default=8)
    thumbs_per_page = db.IntegerProperty(default=12)    
    
    def save(self):
        self.put()
        
gallery_settings=None
def InitGallerySettings():
    global gallery_settings
    gallery_settings = GallerySettings(key_name = "defaultsettings")
    #gallery_settings.domain=os.environ["HTTP_HOST"]
    #gallery_settings.baseurl="http://"+gallery_settings.domain
    gallery_settings.title = "GAE Photos"
    gallery_settings.description = "Photo gallery based on GAE"
    gallery_settings.albums_per_page = 8
    gallery_settings.thumbs_per_page = 12
    gallery_settings.save()
    return gallery_settings


def InitGallery():
    global gallery_settings
    gallery_settings = GallerySettings.get_by_key_name("defaultsettings")
    if not gallery_settings:
        gallery_settings=InitGallerySettings()
        logging.info('gallery setting reloaded')
    gallery_settings.baseurl = "http://"+os.environ["HTTP_HOST"] 
    return gallery_settings

InitGallery()

class CCPhotoModel(db.Model):
    @property
    def id(self):
        return self.key().id()

class Album(CCPhotoModel):
    name = db.StringProperty(multiline=False)
    description = db.StringProperty(default="description", multiline=True)
    public = db.BooleanProperty(default=True)
    createdate = db.DateTimeProperty(auto_now_add=True)
    updatedate = db.DateTimeProperty(auto_now=True)
    photoslist = db.ListProperty(long)
    coverphotoid = db.IntegerProperty()
        
    @staticmethod
    def GetAlbumByID(id):
        album = Album.get_by_id(id)
        return album
    
    @staticmethod
    def GetAlbumByName(name):
        q = db.GqlQuery("SELECT * FROM Album Where name=:1", name)
        li = q.fetch(1)
        return li and li[0] 
    
    @staticmethod
    def CheckAlbumExist(name):
        if Album.GetAlbumByName(name):
            return True
        return False
    
    @staticmethod
    def GetPublicAlbums(public=True):
        albums = Album.all().filter("public =", public)
        return albums
    
    @property
    def photoCount(self):
        return len(self.photoslist)
    
    @property
    def coverPhotoID(self):
        if self.coverphotoid:
            return self.coverphotoid
        if self.photoslist:
            return self.photoslist[0]
        return None
    
    def SetCoverPhoto(self,photoid):
        self.coverphotoid = photoid
        self.put()
    
    def GetPhotos(self):
        photos = Photo.all().filter("album =", self).order("-updatedate")
        return photos
        
    def GetPhotoByName(self, photoname):
        photo = Photo.all().filter("album =", self).filter("name =", photoname)
        photo = photo.fetch(1)
        if photo:
            return photo[0]
        return None
    
    def GetPhotoByID(self, photoid):
        if photoid not in self.photoslist:
            return None
        photo = Photo.GetPhotoByID(photoid)
        return photo
        
class Photo(CCPhotoModel):
    album = db.ReferenceProperty(Album)
    
    name = db.StringProperty()
    owner = db.StringProperty()
    mime = db.StringProperty()
    size = db.IntegerProperty()
    createdate = db.DateTimeProperty(auto_now_add=True)
    updatedate = db.DateTimeProperty(auto_now_add=True)
    description = db.StringProperty(multiline=True)
    width = db.IntegerProperty()
    height = db.IntegerProperty()
    contenttype = db.StringProperty(multiline=False)
    binary = db.BlobProperty() 
    binary_thumb = db.BlobProperty()
    
    commentcount = db.IntegerProperty(default=0)
    
    @staticmethod
    def GetPhotoByID(id):
        photo = Photo.get_by_id(id)
        return photo
    
    @property
    def isPublic(self):
        return self.album.public
    
    @property
    def Comments(self):
        return self.GetComments()
        
    def Save(self):
        self.updatedate = datetime.now()
        self.put()
        if self.id in self.album.photoslist:
            self.album.photoslist.remove(self.id)
        self.album.photoslist.insert(0,self.id)
        self.album.put()
        
    def Delete(self):
        if self.id in self.album.photoslist:
            self.album.photoslist.remove(self.id)
            self.album.put()
        for comment in self.Comments:
            comment.delete()
        self.delete()
        
    def GetComments(self):
        comments = Comment.all().filter("photo =", self)
        return comments
    
    def AddComment(self, author, content):
        comment = Comment(content = content)
        comment.photo = self
        comment.author = author
        comment.Save()
        
    def RemoveComment(self, commentid):
        comment = Comment.get_by_id(commentid)
        if comment and comment.photo == self:
            comment.Delete()

class Comment(CCPhotoModel):
    author = db.StringProperty()
    date = db.DateTimeProperty(auto_now_add=True)
    photo = db.ReferenceProperty(Photo)
    content = db.StringProperty(required=True, multiline=True)    

    def Save(self):
        self.put()
        if not self.photo.commentcount:
            self.photo.commentcount = 0
        self.photo.commentcount+=1
        self.photo.put()
        
    def Delete(self):
        if self.photo.commentcount:
            self.photo.commentcount-=1
            self.photo.put()
        self.delete()
    
    
    