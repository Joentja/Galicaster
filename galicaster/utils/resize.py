# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/utils/resize
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.

from gi.repository import Pango

def _font_attrs(size, bold):
    attrs = Pango.AttrList()
    if size:
        attrs.insert(Pango.attr_size_new(int(size * Pango.SCALE)))
    if bold:
        attrs.insert(Pango.attr_weight_new(Pango.Weight.BOLD))
    return attrs

def relabel(label, size, bold):
    label.set_attributes(_font_attrs(size, bold))

def relabel_updating_font(label, size, bold):
    font = _font_attrs(size, bold)
    label.set_attributes(font)
    return font

def resize_button(button, **kwargs):
    size_image = kwargs.get('size_image')
    if size_image:
        button.set_size_request(int(size_image), int(size_image))
    return button
