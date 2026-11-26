# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/plugins/shortcuts
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.
"""
Keyboard shortcuts plugin (GTK4): the main window emits
'action-key-press' with (window, keyval, state).
"""

from gi.repository import Gdk
from galicaster.core import context


def init():
    dispatcher = context.get_dispatcher()
    dispatcher.connect('action-key-press', check_key)


def check_key(element, source, keyval, state):
    """
    Filter Ctrl combinations for quit and fullscreen toggle
    """
    dispatcher = context.get_dispatcher()
    window = context.get_mainwindow()
    if ((state & Gdk.ModifierType.SHIFT_MASK and state & Gdk.ModifierType.CONTROL_MASK)
            and state & Gdk.ModifierType.MOD2_MASK
            and keyval in [Gdk.keyval_from_name('q'), Gdk.keyval_from_name('Q')]):
        if not context.get_recorder().is_recording():
            dispatcher.emit('action-quit')
    if (state & Gdk.ModifierType.CONTROL_MASK
            and keyval == Gdk.keyval_from_name('Return')):
        window.toggle_fullscreen(None)
    return True
