# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/classui/strip
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.
"""
Status strip shown at the bottom of the main window (GTK4)
"""

from gi.repository import Gtk

from galicaster.core import context
from galicaster.classui import message
from galicaster.utils import readable
from galicaster.utils.i18n import _


class StripUI(Gtk.Box):
    def __init__(self, back_page=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        self.set_margin_start(12)
        self.set_margin_end(12)

        self.repo = context.get_repository()
        self.conf = context.get_conf()
        self.dispatcher = context.get_dispatcher()

        self.space_label = Gtk.Label(xalign=0)
        self.net_label = Gtk.Label(xalign=0)
        self.ops_label = Gtk.Label(xalign=0)
        self.agent_label = Gtk.Label(xalign=0)

        about = Gtk.Button(label=_("About"))
        about.connect('clicked', self.show_about_dialog)

        self.append(self.space_label)
        self.append(self.net_label)
        self.append(self.ops_label)
        self.append(self.agent_label)
        filler = Gtk.Box()
        filler.set_hexpand(True)
        self.append(filler)
        self.append(about)

        self.dispatcher.connect_ui('opencast-status', self.set_net)
        self.dispatcher.connect_ui('operation-started', self.set_ops)
        self.dispatcher.connect_ui('operation-stopped', self.set_ops)
        self.dispatcher.connect_ui('timer-short', self.refresh_space)
        self.dispatcher.connect_ui('init', self.refresh_space)
        self.refresh()

    def refresh(self):
        self.refresh_space()
        self.agent_label.set_text(self.conf.get_hostname())
        if not self.conf.get_boolean('ingest', 'active'):
            self.set_net(None, None)

    def refresh_space(self, *args):
        freespace = self.repo.get_free_space()
        hours = int(freespace / 4000000000.0)
        self.space_label.set_text(_("{0} ({1} hours left)").format(
            readable.size(freespace), hours))
        return True

    def set_net(self, origin, status=None):
        if status is True:
            self.net_label.set_text(_("Opencast: Up"))
            self.net_label.set_css_classes(['green_coloured'])
        elif status is False:
            self.net_label.set_text(_("Opencast: Down"))
            self.net_label.set_css_classes(['red_coloured'])
        else:
            self.net_label.set_text(_("Opencast: Disabled"))
            self.net_label.set_css_classes(['gray_coloured'])

    def set_ops(self, origin, code=None, mp=None, success=None, exc=None):
        from galicaster.core.worker import JOB_NAMES
        from galicaster.mediapackage.mediapackage import op_status
        if code and mp is not None:
            status = op_status[mp.getOpStatus(code)]
            self.ops_label.set_text("{0}: {1}".format(JOB_NAMES.get(code, code), status))

    def show_about_dialog(self, button):
        text = {"title": _("About Galicaster"),
                "main": _("Galicaster capture agent (GTK4 rebuild)")}
        message.PopUp(message.ABOUT, text, context.get_mainwindow())

    def resize(self):
        pass
