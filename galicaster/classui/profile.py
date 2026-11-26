# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/classui/profile
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.
"""
Profile picker dialog (GTK4): lists the available profiles and their
tracks (video sources with embedded audio sources) and loads the selected
one as the current profile.
"""

from gi.repository import Gtk

from galicaster.core import context
from galicaster.classui import widget_children
from galicaster.utils.i18n import _

logger = context.get_logger()


class ProfileDialog(Gtk.Window):
    def __init__(self, parent=None):
        super().__init__(title=_("Select profile"))
        if parent is not None:
            self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(640, 400)
        self.set_hide_on_close(True)

        self.conf = context.get_conf()
        self.dispatcher = context.get_dispatcher()

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer.set_margin_top(12)
        outer.set_margin_bottom(12)
        outer.set_margin_start(12)
        outer.set_margin_end(12)

        info = Gtk.Label(label=_("Choose a capture profile. Each profile defines "
                                 "the video sources and their embedded audio sources."),
                         xalign=0, wrap=True)
        outer.append(info)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect('row-selected', self.on_row_selected)
        scroll.set_child(self.listbox)
        outer.append(scroll)

        self.detail = Gtk.Label(xalign=0, wrap=True)
        outer.append(self.detail)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        load = Gtk.Button(label=_("Load profile"))
        load.connect('clicked', self.on_load)
        cancel = Gtk.Button(label=_("Cancel"))
        cancel.connect('clicked', lambda b: self.close())
        buttons.append(cancel)
        buttons.append(load)
        outer.append(buttons)

        self.set_child(outer)
        self.refresh()

    def refresh(self):
        for child in list(widget_children(self.listbox)):
            self.listbox.remove(child)

        current = self.conf.get_current_profile()
        for name, profile in self.conf.get_profiles().items():
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            row.set_margin_top(6)
            row.set_margin_bottom(6)
            title = Gtk.Label(xalign=0)
            marker = "* " if current and profile.name == current.name else ""
            title.set_markup("<b>{}{}</b>".format(marker, name))
            row.append(title)
            summary = Gtk.Label(xalign=0)
            summary.set_markup("<small>{}</small>".format(self.tracks_summary(profile)))
            row.append(summary)
            self.listbox.append(row)

    def tracks_summary(self, profile):
        parts = []
        for track in profile.tracks:
            parts.append("{0} ({1}, {2})".format(track.name, track.device, track.flavor))
        return "  ".join(parts)

    def on_row_selected(self, listbox, row):
        if row is None:
            return
        index = row.get_index()
        profiles = list(self.conf.get_profiles().values())
        if 0 <= index < len(profiles):
            self.detail.set_text(self.tracks_summary(profiles[index]))

    def on_load(self, button):
        row = self.listbox.get_selected_row()
        if row is None:
            return
        index = row.get_index()
        profiles = list(self.conf.get_profiles().items())
        if 0 <= index < len(profiles):
            name = profiles[index][0]
            logger.info("Loading profile {}".format(name))
            self.conf.change_current_profile(name)
            self.dispatcher.emit("action-reload-profile")
            self.close()

    def close(self, *args):
        self.hide()
        return True
