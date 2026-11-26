# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/plugins/lockscreen
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.
"""
Lockscreen plugin (GTK4): shows a modal password dialog on init and
after each finished recording.
"""
from galicaster.core import context
from galicaster.utils.i18n import _
from gi.repository import Gtk

conf = None
logger = None


def init():
    global conf, logger
    dispatcher = context.get_dispatcher()
    logger = context.get_logger()
    conf = context.get_conf()
    dispatcher.connect('init', show_msg)
    dispatcher.connect('record-finished', show_msg)


def show_msg(element=None, *args):
    text = _("Please insert the password")
    lock(text)


def lock(text):
    parent = context.get_mainwindow()
    dialog = Gtk.Window(title=_("Lock screen"))
    dialog.set_transient_for(parent)
    dialog.set_modal(True)

    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    outer.set_margin_top(16)
    outer.set_margin_bottom(16)
    outer.set_margin_start(20)
    outer.set_margin_end(20)

    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    icon = Gtk.Image.new_from_icon_name("dialog-password")
    icon.set_pixel_size(48)
    box.append(icon)
    box.append(Gtk.Label(label=text, xalign=0))
    outer.append(box)

    entry = Gtk.Entry()
    entry.set_visibility(False)
    entry.set_placeholder_text(_("Password"))
    outer.append(entry)

    buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    buttons.set_halign(Gtk.Align.END)
    quit_button = conf.get_boolean('lockscreen', 'enable_quit_button')
    if quit_button:
        quitb = Gtk.Button(label=_("Quit"))
        quitb.connect('clicked', lambda b: parent.do_quit())
        buttons.append(quitb)
    ok = Gtk.Button(label=_("Unlock"))
    ok.connect('clicked', on_unlock, dialog, entry)
    buttons.append(ok)
    outer.append(buttons)

    dialog.set_child(outer)
    dialog.present()
    logger.info("Galicaster locked")


def on_unlock(button, dialog, entry):
    password = conf.get('lockscreen', 'password')
    if entry.get_text() == password:
        dialog.close()
    else:
        entry.set_text("")
