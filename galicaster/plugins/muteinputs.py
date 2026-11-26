# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/plugins/muteinputs
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.
"""
Plugin that adds an input mute toggle button to the recorder page (GTK4)
"""

from galicaster.core import context
from galicaster.core.core import PAGES
from galicaster.utils.i18n import _
from gi.repository import Gtk

conf = None
logger = None
recorder = None
dispatcher = None


def init():
    global conf, logger, recorder, dispatcher
    dispatcher = context.get_dispatcher()
    logger = context.get_logger()
    conf = context.get_conf()
    recorder = context.get_recorder()
    dispatcher.connect('init', manage_button)


def manage_button(element=None):
    recorder.enable_input()
    label = Gtk.Label(label=_("Input status: "), xalign=0)
    label1 = Gtk.Label(label="", xalign=0)

    to_disable = conf.get("muteinputs", "bins")
    to_disable = [] if to_disable == "" else [b.strip() for b in to_disable.split(",")]
    mute_type = conf.get_choice("muteinputs", "mute_type", ["input", "preview"], "input")
    started_mute = conf.get_boolean("muteinputs", "mute_on_startup")

    button = Gtk.ToggleButton()
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    icon = Gtk.Image.new_from_icon_name("video-display")
    icon.set_pixel_size(32)
    hbox.append(icon)
    hbox.append(Gtk.Label(label=_("Mute inputs")))
    button.set_child(hbox)

    page = context.get_mainwindow().get_page(PAGES['REC'])
    tool = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    tool.append(label)
    tool.append(label1)
    tool.append(button)
    page.add_tool(tool)

    button.connect("clicked", mute_inputs, mute_type, label1, to_disable)
    if started_mute:
        button.set_active(True)
    dispatcher.connect("recorder-ready", reload_mute, mute_type, label1, started_mute, button, to_disable)
    set_status_label(label1, mute_type)


def mute_inputs(button, mute_type, label, to_disable):
    if button.get_active():
        if mute_type == "input":
            recorder.disable_input(to_disable)
        else:
            recorder.disable_preview(to_disable)
        label.set_text(_("Muted"))
    else:
        if mute_type == "input":
            recorder.enable_input(to_disable)
        else:
            recorder.enable_preview(to_disable)
        label.set_text(_("Active"))


def reload_mute(element, mute_type, label, started_mute, button, to_disable):
    if started_mute:
        button.set_active(True)
    else:
        button.set_active(False)
    set_status_label(label, mute_type)


def set_status_label(label, mute_type):
    status = recorder.get_mute_status()
    key = "input" if mute_type == "input" else "preview"
    muted = status.get(key, {}) and not all(status[key].values())
    label.set_text(_("Muted") if muted else _("Active"))
