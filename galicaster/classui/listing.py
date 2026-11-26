# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/classui/listing
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.
"""
Recordings (media manager) view (GTK4): lists the previously recorded
sessions in the local repository and lets the user ingest them to
Opencast, export them to zip or delete them.
"""

import datetime

from gi.repository import Gtk

from galicaster.core import context
from galicaster.classui import message
from galicaster.mediapackage.mediapackage import op_status
from galicaster.utils import readable
from galicaster.utils.i18n import _

logger = context.get_logger()

COLUMNS = ['title', 'date', 'duration', 'status', 'id']


class ListingClassUI(Gtk.Box):
    """
    Graphic User Interface for the recordings list (GTK4)
    """

    __gtype_name__ = 'ListingClass'

    def __init__(self):
        logger.info("Creating Recordings List (GTK4)")
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(6)
        self.set_margin_end(6)

        self.repo = context.get_repository()
        self.dispatcher = context.get_dispatcher()
        self.worker = context.get_worker()
        self.conf = context.get_conf()

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        back = Gtk.Button(label=_("Back to recorder"))
        back.connect('clicked', self.on_back)
        top.append(back)

        refresh = Gtk.Button(label=_("Refresh"))
        refresh.connect('clicked', lambda b: self.refresh())
        top.append(refresh)

        self.play_button = Gtk.Button(label=_("Play"))
        self.play_button.connect('clicked', self.on_play)
        top.append(self.play_button)

        self.ingest_button = Gtk.Button(label=_("Ingest"))
        self.ingest_button.connect('clicked', self.on_ingest)
        top.append(self.ingest_button)

        zip_button = Gtk.Button(label=_("Export to Zip"))
        zip_button.connect('clicked', self.on_zip)
        top.append(zip_button)

        info_button = Gtk.Button(label=_("Info"))
        info_button.connect('clicked', self.on_info)
        top.append(info_button)

        edit_button = Gtk.Button(label=_("Edit metadata"))
        edit_button.connect('clicked', self.on_edit)
        top.append(edit_button)

        delete_button = Gtk.Button(label=_("Delete"))
        delete_button.connect('clicked', self.on_delete)
        top.append(delete_button)

        self.append(top)

        self.store = Gtk.ListStore(str, str, str, str, str)
        self.treeview = Gtk.TreeView(model=self.store)
        self.treeview.set_vexpand(True)
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
        self.treeview.get_selection().connect('changed', self.on_selection_changed)
        self.treeview.connect('row-activated', self.on_double_click)

        titles = [_("Title"), _("Date"), _("Duration"), _("Status"), _("Id")]
        for i, title in enumerate(titles):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            column.set_resizable(True)
            column.set_sort_column_id(i)
            self.treeview.append_column(column)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(self.treeview)
        self.append(scroll)

        self.dispatcher.connect_ui('action-mm-refresh-row', self.refresh_row_from_mp)
        self.dispatcher.connect_ui('operation-stopped', self.refresh_row_from_mp_id)
        self.dispatcher.connect_ui('view-changed', self.on_view_changed)

        self.refresh()

    def on_back(self, button):
        self.dispatcher.emit("action-view-change", 0)

    def on_view_changed(self, orig, old, new):
        if new == 1:
            self.refresh()

    def get_selected_mp(self):
        model, iter = self.treeview.get_selection().get_selected()
        if iter is None:
            return None
        mp_id = model.get_value(iter, 4)
        return self.repo[mp_id] if mp_id in self.repo else None

    def on_selection_changed(self, selection):
        has = self.get_selected_mp() is not None
        self.play_button.set_sensitive(has)
        self.ingest_button.set_sensitive(has and self.conf.get_boolean('ingest', 'active'))

    def populate_treeview(self):
        self.store.clear()
        mps = sorted(self.repo.values(), key=lambda mp: mp.getDate() or datetime.datetime.min, reverse=True)
        for mp in mps:
            self.insert_row(mp)

    def insert_row(self, mp):
        date = mp.getDate()
        date_str = date.strftime("%Y-%m-%d %H:%M") if date else ""
        duration = readable.long_time(datetime.timedelta(milliseconds=mp.getDuration())) if mp.getDuration() else ""
        ops = ", ".join("{0}:{1}".format(code, op_status[mp.getOpStatus(code)]) for code in mp.operations)
        status = str(mp.status) + ((" (" + ops + ")") if ops else "")
        self.store.append([mp.getTitle(), date_str, duration, status, mp.getIdentifier()])

    def refresh(self, element=None, package=None):
        self.populate_treeview()

    def refresh_row_from_mp(self, origin, identifier):
        self.refresh()

    def refresh_row_from_mp_id(self, origin, code, mp, success=None, exc=None):
        self.refresh()

    def on_play(self, button):
        mp = self.get_selected_mp()
        if mp:
            self.dispatcher.emit('play-list', mp)

    def on_ingest(self, button):
        mp = self.get_selected_mp()
        if mp:
            self.worker.enqueue_job_by_name('ingest', mp)

    def on_zip(self, button):
        mp = self.get_selected_mp()
        if mp:
            self.worker.enqueue_job_by_name('exporttozip', mp)

    def on_info(self, button):
        mp = self.get_selected_mp()
        if mp:
            text = {"title": mp.getTitle(),
                    "main": _("Id: {0}").format(mp.getIdentifier()),
                    "text": _("Date: {0}\nStatus: {1}\nDuration: {2}").format(
                        mp.getDate(), mp.status, mp.getDuration())}
            message.PopUp(message.MP_INFO, text, context.get_mainwindow())

    def on_edit(self, button):
        from galicaster.classui.metadata import MetadataClass
        mp = self.get_selected_mp()
        if mp:
            MetadataClass(mp, parent=context.get_mainwindow())
            self.refresh()

    def on_delete(self, button):
        mp = self.get_selected_mp()
        if not mp:
            return
        text = {"title": _("Delete recording"),
                "main": _("Are you sure you want to delete\n{0}?").format(mp.getTitle())}
        buttons = (("_Delete", Gtk.ResponseType.OK), ("_Cancel", Gtk.ResponseType.REJECT))
        message.PopUp(message.WARN_DELETE, text, context.get_mainwindow(), buttons,
                      lambda response_id: self.on_delete_response(response_id, mp))

    def on_delete_response(self, response_id, mp):
        if response_id in message.POSITIVE:
            self.repo.delete(mp)
            self.refresh()

    def on_double_click(self, treeview, path, column):
        self.on_play(None)

    def resize(self):
        return True

