# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/plugins/script_button
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.
"""
Plugin that adds custom script buttons to the recorder page (GTK4)
"""
import json
import subprocess
from gi.repository import Gtk
from galicaster.core.core import PAGES
from galicaster.core import context
from galicaster.utils.i18n import _

logger = context.get_logger()
conf = context.get_conf()


def init(**kwargs):
    buttons_conf = conf.get_section('script_button')
    for name, button_conf in list(buttons_conf.items()):
        button_conf = json.loads(button_conf)
        ScriptButton(button_conf['name'], button_conf['icon'], button_conf['command'])


class ScriptButton:
    def __init__(self, name, icon, command):
        self.name = name
        self.icon = icon
        self.command = command
        dispatcher = context.get_dispatcher()
        dispatcher.connect('init', self.__configure_layout)

    def __configure_layout(self, element=None):
        page = context.get_mainwindow().get_page(PAGES['REC'])
        button = self.__create_button(self.name, self.icon)
        page.add_tool(button)

    def __create_button(self, name, icon):
        logger.info("Creating button {}".format(name))
        button = Gtk.Button()
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon_img = Gtk.Image.new_from_icon_name(icon)
        icon_img.set_pixel_size(24)
        hbox.append(icon_img)
        hbox.append(Gtk.Label(label=_(name)))
        button.set_child(hbox)
        button.connect("clicked", self.__handler_script_button)
        return button

    def __handler_script_button(self, element=None):
        process = subprocess.Popen(self.command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        logger.info("Script button {} output: {}".format(self.name, output))
