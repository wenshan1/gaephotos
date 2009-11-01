#!/usr/bin/env python
# -*- coding: utf-8 -*-   
from django import template
from django.template import Node,NodeList,resolve_variable
from django.template import TemplateSyntaxError,VariableDoesNotExist,TokenParser

register = template.Library()

from cc_addons.language import translate

class TranslateNode(Node):
    def __init__(self, value, noop):
        self.value = value
        self.noop = noop

    def render(self, context):
        value = resolve_variable(self.value, context)
        if self.noop:
            return value
        else:
            return translate(value)
   
def do_translate(parser, token):
    class TranslateParser(TokenParser):
        def top(self):
            value = self.value()
            if self.more():
                if self.tag() == 'noop':
                    noop = True
                else:
                    raise TemplateSyntaxError, "only option for 'trans' is 'noop'"
            else:
                noop = False
            return (value, noop)
        
    value, noop = TranslateParser(token.contents).top()
    return TranslateNode(value, noop)





