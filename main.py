#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys

#code = sys.getdefaultencoding()  
#if code != 'utf8': 
#    reload(sys)  
#    sys.setdefaultencoding('utf8')  
    
# Google App Engine imports.
from google.appengine.ext.webapp import util

# Force Django to reload its settings.
from django.conf import settings
settings._target = None

# Must set this env var before importing any part of Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import logging
import django.core.handlers.wsgi
import django.core.signals
import django.db
import django.dispatch.dispatcher

def log_exception(*args, **kwds):
  logging.exception('Exception in request:')

# Log errors.
django.dispatch.dispatcher.connect(
   log_exception, django.core.signals.got_request_exception)

# Unregister the rollback event handler.
django.dispatch.dispatcher.disconnect(
    django.db._rollback_on_exception,
    django.core.signals.got_request_exception)

def main():
  # Create a Django application for WSGI.
  application = django.core.handlers.wsgi.WSGIHandler()

  # Run the WSGI CGI handler with that application.
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()