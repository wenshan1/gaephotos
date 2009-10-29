#!/usr/bin/env python
# -*- coding: utf-8 -*-   
from django import template
from django.template import Node,NodeList,resolve_variable
from django.template import TemplateSyntaxError,VariableDoesNotExist

register = template.Library()

class IfCmpNode(Node):
    def __init__(self, var1, var2, var3, nodelist_true, nodelist_false):
        self.left, self.right = var1, var3
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false
        self.opr = var2

    def __repr__(self):
        return "<IfCmpNode>"

    def render(self, context):
        try:
            left = resolve_variable(self.left, context)
        except VariableDoesNotExist:
            left = None
        try:
            right = resolve_variable(self.right, context)
        except VariableDoesNotExist:
            right = None
        compare_status = eval("left %s right" % self.opr)
        if compare_status:
            return self.nodelist_true.render(context)
        return self.nodelist_false.render(context)
    
def do_ifcompare(parser, token, opr=None):
    bits = list(token.split_contents())
    if opr == None:
        if len(bits) != 4:
            raise TemplateSyntaxError, \
        "%r takes 3 arguments, {%%%s x > y %%}" % (bits[0],bits[0])
    else:
        if len(bits) != 3:
            raise TemplateSyntaxError, \
        "%r takes 2 arguments, {%%%s x y %%}" % (bits[0],bits[0])
        
    end_tag = 'end' + bits[0]
    nodelist_true = parser.parse(('else', end_tag))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse((end_tag,))
        parser.delete_first_token()
    else:
        nodelist_false = NodeList()
    
    if opr == None:
        return IfCmpNode(bits[1], bits[2], bits[3], nodelist_true, nodelist_false)
    else:
        return IfCmpNode(bits[1], opr, bits[2], nodelist_true, nodelist_false)

OPERATOR_EQ = "=="
OPERATOR_NE = "!="
OPERATOR_GT = ">"
OPERATOR_GE = ">="
OPERATOR_LT = "<"
OPERATOR_LE = "<="

@register.tag
def ifcmp(parser, token):
    return do_ifcompare(parser, token)

@register.tag
def ifeq(parser, token):
    return do_ifcompare(parser, token, OPERATOR_EQ)
@register.tag
def ifne(parser, token):
    return do_ifcompare(parser, token, OPERATOR_NE)
@register.tag
def ifgt(parser, token):
    return do_ifcompare(parser, token, OPERATOR_GT)
@register.tag
def ifge(parser, token):
    return do_ifcompare(parser, token, OPERATOR_GE)
@register.tag
def iflt(parser, token):
    return do_ifcompare(parser, token, OPERATOR_LT)
@register.tag
def ifle(parser, token):
    return do_ifcompare(parser, token, OPERATOR_LE)
