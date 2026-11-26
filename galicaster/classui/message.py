# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/classui/message
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.
"""
Basic Dialog Message UI (GTK4, built in code)
"""

from gi.repository import Gtk

from galicaster.utils.i18n import _
from galicaster.core import context

TEXT = {'title': None, 'main': None, 'text': None}

INFO = 'info'
ERROR = 'error'
WARN_STOP = 'stop'
WARN_QUIT = 'quit'
WARN_DELETE = 'delete'
WARN_OK = 'okwarning'
OPERATIONS = 'operations'
ABOUT = 'about'
LOCKSCREEN = 'lockscreen'
MP_INFO = 'mp_info'
NEXT_REC = 'next_rec'

POSITIVE = [
    Gtk.ResponseType.ACCEPT,
    Gtk.ResponseType.OK,
    Gtk.ResponseType.YES,
    Gtk.ResponseType.APPLY
]
NEGATIVE = [
    Gtk.ResponseType.REJECT,
    Gtk.ResponseType.DELETE_EVENT,
    Gtk.ResponseType.CANCEL,
    Gtk.ResponseType.CLOSE,
    Gtk.ResponseType.NO
]

OPERATION_NAMES = {
    'Export to Zip': _('Export to Zip'),
    'Export to Zip Nightly': _('Export to Zip Nightly'),
    'Cancel Export to Zip Nightly': _('Cancel Zip Nightly'),
    'Ingest': _('Ingest'),
    'Ingest Nightly': _('Ingest Nightly'),
    'Cancel Ingest Nightly': _('Cancel Ingest Nightly'),
    'Side by Side': _('Side by Side'),
    'Side by Side Nightly': _('Side by Side Nightly'),
    'Cancel Side by Side Nightly': _('Cancel SbS Nightly'),
    'Cancel': _('Cancel'),
}

instance = None

ICONS = {
    INFO: 'dialog-information',
    ERROR: 'dialog-error',
    WARN_STOP: 'dialog-warning',
    WARN_QUIT: 'dialog-warning',
    WARN_DELETE: 'dialog-warning',
    WARN_OK: 'dialog-warning',
    ABOUT: 'dialog-information',
    NEXT_REC: 'dialog-information',
    MP_INFO: 'dialog-information',
    OPERATIONS: 'dialog-question',
    LOCKSCREEN: 'dialog-password',
}


class PopUp(object):
    """Handle a pop up for warnings and questions (GTK4)"""

    def __init__(self, message=None, text=TEXT, parent=None,
                 buttons=None, response_action=None, close_on_response=True,
                 show=[], close_parent=False, close_before_response_action=False):
        """Builds a modal dialog in code.
        Args:
            message (str): type of message (see constants above)
            text (Dict{str:str}): 'title', 'main' and 'text' labels; NEXT_REC also accepts 'next_recs'
            parent (Gtk.Window): main window
            buttons: iterable of (label, response_id) pairs
        """
        global instance
        instance = self

        self.response_action = response_action
        self.close_on_response = close_on_response
        self.close_before_response_action = close_before_response_action
        self.message = message
        self.close_parent = close_parent
        self.dispatcher = context.get_dispatcher()

        self.dialog = Gtk.Window(title=text.get('title') or _("Galicaster"))
        if parent is not None:
            self.dialog.set_transient_for(parent)
        self.dialog.set_modal(True)
        self.dialog.set_hide_on_close(True)
        self.dialog.connect('close-request', self.dialog_destroy)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(18)
        outer.set_margin_bottom(18)
        outer.set_margin_start(24)
        outer.set_margin_end(24)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        icon = Gtk.Image.new_from_icon_name(ICONS.get(message, 'dialog-information'))
        icon.set_pixel_size(48)
        header.append(icon)
        title = Gtk.Label(label=text.get('title') or _("Galicaster"), xalign=0)
        title.add_css_class('dialog_title')
        header.append(title)
        outer.append(header)

        if text.get('main'):
            main = Gtk.Label(label=text['main'], xalign=0, wrap=True)
            main.add_css_class('dialog_body')
            outer.append(main)

        if text.get('text'):
            scroll = Gtk.ScrolledWindow()
            scroll.set_min_content_height(120)
            scroll.set_min_content_width(420)
            scroll.set_vexpand(True)
            body = Gtk.Label(label=text['text'], xalign=0, yalign=0, wrap=True, selectable=True)
            body.add_css_class('dialog_body')
            scroll.set_child(body)
            outer.append(scroll)

        if message == NEXT_REC and text.get('next_recs'):
            listbox = Gtk.ListBox()
            listbox.add_css_class('next_recs')
            for info in text['next_recs']:
                row = Gtk.Label(xalign=0)
                row.set_markup("<b>{title}</b>\t{date}\t{duration}".format(
                    title=info.get('title', ''), date=info.get('date', ''),
                    duration=info.get('duration', '')))
                listbox.append(row)
            outer.append(listbox)

        buttons = buttons or (("_OK", Gtk.ResponseType.OK),)
        if isinstance(buttons, dict):
            buttons = list(buttons.items())
        bbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bbox.set_halign(Gtk.Align.END)
        for item in buttons:
            label, response = item[0], item[1]
            button = Gtk.Button(label=_(label) if not label.startswith('_') else _(label))
            button.connect('clicked', self.on_dialog_response, response)
            bbox.append(button)
        outer.append(bbox)

        self.dialog.set_child(outer)
        self.dialog.present()

    def on_dialog_response(self, button, response_id):
        if self.close_before_response_action and self.close_parent:
            pass
        if self.response_action:
            self.response_action(response_id)
        if self.close_on_response:
            self.dialog_destroy()

    def force_response(self, origin=None, response=None):
        if self.response_action:
            self.response_action(response)
        self.dialog_destroy()

    def dialog_destroy(self, *args):
        if self.dialog:
            self.dialog.close()
            self.dialog = None
        return True
