#!/usr/bin/env python
#coding:utf-8
# Author:  CChen
# Purpose: package
# Created: 12/29/2009

import os,sys
import stat,fnmatch
import zipfile
import hashlib

def getFileList(path, ext, subdir = True ):
    if os.path.exists(path):
        dirlist = []

        for name in os.listdir(path):
            fullname = os.path.join(path, name)
            st = os.lstat(fullname)
            if stat.S_ISDIR(st.st_mode) and subdir:
                dirlist +=  getFileList(fullname,ext)
            elif os.path.isfile(fullname):
                if fnmatch.fnmatch( fullname, ext):  
                    dirlist.append(fullname)
            else:
                pass 
        return dirlist
    else:
        return []

Package_Name = "GAEPhotos_v0.1.zip"
Base_Path = os.path.abspath(os.path.dirname(os.path.realpath(__file__))) 

included_exts = ["*.*"]
excluded_files = ["pack.py",Package_Name]   
    
def package():
    zfile = zipfile.ZipFile(os.path.join(Base_Path,Package_Name), mode='w')
    
    for ext in included_exts:
      filelist = getFileList(Base_Path, ext, True)
      for f in filelist:
         writefiletozipwithrule(f, zfile)

    zfile.close()
    
def writefiletozipwithrule(filepath, zfile):
    print('packing file %s'%filepath)
    shortname = filepath.replace(Base_Path+'\\','')
    if shortname not in excluded_files:
        shortname = filepath.replace(Base_Path,'')
        zfile.write(filepath, shortname, zipfile.ZIP_DEFLATED)        
        
if __name__=='__main__':
    package()
    
    
    
