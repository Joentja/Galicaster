# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/classui/metadata
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.
"""
Metadata editor dialog (GTK4, built in code)
"""

from gi.repository import Gtk

import os

from galicaster.mediapackage import mediapackage
from galicaster.opencast import series as utils_series
from galicaster.core import context
from galicaster.utils.i18n import _

NO_SERIES = "** NO SERIES SELECTED **"

DCTERMS = ["title", "creator", "description", "language", "isPartOf"]
EQUIV = {"presenter": "creator", "ispartof": "isPartOf", "series": "isPartOf"}

FIELD_LABELS = {
    "title": _("Title:"),
    "creator": _("Presenter:"),
    "isPartOf": _("Course/Series:"),
    "description": _("Description:"),
    "language": _("Language:"),
}


class MetadataClass:
    """
    Pop-up metadata editor for a mediapackage (GTK4)
    """

    def __init__(self, package=None, parent=None,
                 title=_("Edit Metadata"), subtitle=_("Edit Metadata"),
                 ok_label=_("Save"), ko_label=_("Cancel"),
                 empty_series_label=NO_SERIES):
        if parent is None:
            parent = context.get_mainwindow()
        self.par = parent
        self.package = package
        self.empty_series_label = empty_series_label

        ocservice = context.get_ocservice()
        self.series_list = ocservice.series if ocservice else []

        conf = context.get_conf()
        blocked = set()
        mandatory = set()
        try:
            for term in conf.get('metadata', 'blocked').split():
                blocked.add(EQUIV.get(term, term))
        except (KeyError, AttributeError):
            pass
        try:
            for term in conf.get('metadata', 'mandatory').split():
                mandatory.add(EQUIV.get(term, term))
        except (KeyError, AttributeError):
            pass

        self.dialog = Gtk.Window(title=title)
        self.dialog.set_transient_for(parent)
        self.dialog.set_modal(True)
        self.dialog.set_default_size(640, -1)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(16)
        outer.set_margin_bottom(16)
        outer.set_margin_start(20)
        outer.set_margin_end(20)

        header = Gtk.Label(label=subtitle, xalign=0)
        header.add_css_class('dialog_title')
        outer.append(header)

        self.grid = Gtk.Grid(column_spacing=10, row_spacing=8)
        self.entries = {}
        self.mandatory = {}
        self.save_button = Gtk.Button(label=ok_label)
        self.save_button.connect('clicked', self.on_save)

        row = 0
        for meta in DCTERMS:
            label = Gtk.Label(label=FIELD_LABELS[meta], xalign=0)
            self.grid.attach(label, 0, row, 1, 1)

            if meta == "isPartOf":
                widget = self.__build_series_combo(package)
            else:
                widget = Gtk.Entry()
                try:
                    widget.set_text(package.metadata_episode[meta] or '')
                except (KeyError, AttributeError):
                    widget.set_text('')

            widget.set_name(meta)
            widget.set_hexpand(True)
            if meta in blocked:
                widget.set_sensitive(False)
            if meta in mandatory:
                widget.connect('changed', self.check_mandatory, self.save_button)
                self.mandatory[widget] = label
            self.grid.attach(widget, 1, row, 1, 1)
            self.entries[meta] = widget
            row += 1

        outer.append(self.grid)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label=ko_label)
        cancel.connect('clicked', lambda b: self.dialog.close())
        buttons.append(cancel)
        buttons.append(self.save_button)
        outer.append(buttons)

        self.dialog.set_child(outer)
        self.check_mandatory(None, self.save_button, check_all=True)
        self.dialog.present()

    def __build_series_combo(self, package):
        combo = Gtk.ComboBoxText()
        combo.append_text(self.empty_series_label)
        current_id = None
        try:
            current_id = package.metadata_series['identifier']
        except (KeyError, AttributeError, TypeError):
            pass
        default_id = None
        try:
            default_id = utils_series.filterSeriesbyId(self.series_list, current_id)['id']
        except Exception:
            default_id = None
        for element in self.series_list:
            combo.append(element[0], element[1]['title'])
        if default_id is not None:
            combo.set_active_id(default_id)
        else:
            combo.set_active(0)
        return combo

    def check_mandatory(self, item, button, check_all=False):
        entries = list(self.mandatory.keys())
        if not check_all and item in entries:
            entries.insert(0, entries.pop(entries.index(item)))

        button.set_sensitive(True)
        for elem in entries:
            content = None
            if isinstance(elem, Gtk.ComboBoxText):
                content = elem.get_active_text()
                if content == self.empty_series_label:
                    content = None
            else:
                content = elem.get_text()

            self.mandatory[elem].set_sensitive(bool(content))
            if not bool(content):
                button.set_sensitive(False)
                if not check_all:
                    break
        return False

    def on_save(self, button):
        self.update_metadata()
        self.dialog.close()

    def update_metadata(self):
        """Write data back to the mediapackage"""
        mp = self.package
        repo = context.get_repository()
        for name, widget in self.entries.items():
            if name in ("creator", "contributor", "subject"):
                value = widget.get_text().strip()
                mp.metadata_episode[name] = value if value else None
            elif name == "isPartOf":
                identifier = widget.get_active_id()
                series = utils_series.filterSeriesbyId(self.series_list, identifier)
                if series:
                    mp.setSeries(series["list"])
                    if not mp.getCatalogs("dublincore/series") and mp.getURI():
                        new_series = mediapackage.Catalog(os.path.join(mp.getURI(), "series.xml"),
                                                          mimetype="text/xml", flavor="dublincore/series")
                        mp.add(new_series)
                else:
                    mp.setSeries(None)
                    catalogs = mp.getCatalogs("dublincore/series")
                    if catalogs:
                        mp.remove(catalogs[0])
            else:
                mp.metadata_episode[name] = widget.get_text()
        repo.update(mp)
        dispatcher = context.get_dispatcher()
        dispatcher.emit('action-mm-refresh-row', mp.identifier)
