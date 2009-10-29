#!/usr/bin/env python
# -*- coding: utf-8 -*-       
from django import template
from django.utils import text

register = template.Library()

def truncate_chinese_words(s, num):
    length = int(num)
    try:
        words = s.decode('ascii')
        return template.defaultfilters.truncatewords(s, length)
    except:
        pass
    words = s
    if len(words) > length:
        words = words[:length]
        if not words[-1].endswith('...'):
            words += ('...')
    return words

register.filter(truncate_chinese_words)        
        
        
        
        
        
        
        
        
        
        
        
        
        