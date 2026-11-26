# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/plugins/noaudiodialog
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.
"""
Plugin that shows a dialog when audio is muted or too low (GTK4).
Shown when: the plugin is active, there is an audio input, the audio
level is lower than the threshold, the page has focus and the dialog
was not blocked or closed. The blockade is cancelled when the profile
is reloaded or changed and when a recording starts.
"""
from gi.repository import Gtk
from galicaster.core import context
from threading import Lock
from galicaster.utils.i18n import _

lock = Lock()
no_audio = False
no_audio_dialog = None
focus_is_active = False
keep_hidden = False
old_keep_hidden = False
was_shown = False


def init():
    global focus_is_active
    global no_audio_dialog
    dispatcher = context.get_dispatcher()
    no_audio_dialog = create_ui()
    dispatcher.connect('audio-mute', warning_audio_show)
    dispatcher.connect('audio-recovered', warning_audio_hide)
    dispatcher.connect('view-changed', event_change_mode)
    dispatcher.connect('action-reload-profile', clear_data_and_check)
    dispatcher.connect('recorder-starting', deactivate_hidden_and_check)
    dispatcher.connect('recorder-upcoming-event', deactivate_hidden_and_check)
    dispatcher.connect('action-audio-disable-msg', force_hide)
    dispatcher.connect('action-audio-enable-msg', disable_force_hide)


def force_hide(element=None):
    global no_audio_dialog
    global was_shown
    global keep_hidden
    global old_keep_hidden
    with lock:
        was_shown = no_audio_dialog.get_visible()
        old_keep_hidden = keep_hidden
        keep_hidden = True
        __check_dialog()


def disable_force_hide(element=None):
    global keep_hidden
    global old_keep_hidden
    global was_shown
    with lock:
        keep_hidden = old_keep_hidden
        if was_shown:
            __check_dialog()


def __check_dialog():
    global no_audio_dialog
    global keep_hidden
    global focus_is_active
    global no_audio
    if not keep_hidden and no_audio and focus_is_active:
        list_toplevels = getattr(Gtk.Window, 'list_toplevels', None)
        if list_toplevels is not None:
            for w in list_toplevels():
                if w.get_modal():
                    return False
        no_audio_dialog.show()
    else:
        no_audio_dialog.hide()


def activate_hidden(button, dialog):
    global keep_hidden
    with lock:
        keep_hidden = True
        __check_dialog()


def deactivate_hidden_and_check(element=None):
    global keep_hidden
    with lock:
        keep_hidden = False
        __check_dialog()
    return True


def clear_data_and_check(element=None):
    global no_audio
    no_audio = False
    with lock:
        __check_dialog()
    return True


def warning_audio_show(element=None):
    global no_audio
    with lock:
        no_audio = True
        __check_dialog()
    return True


def warning_audio_hide(element=None):
    global no_audio
    with lock:
        no_audio = False
        __check_dialog()
    return True


def event_change_mode(orig, old_state, new_state):
    global focus_is_active
    if new_state == 0:
        with lock:
            focus_is_active = True
            __check_dialog()
    if old_state == 0:
        with lock:
            focus_is_active = False
            __check_dialog()


def create_ui():
    """Creates the No Audio Dialog interface (GTK4, built in code)"""
    parent = context.get_mainwindow()
    dialog = Gtk.Window(title=_("Warning"))
    dialog.set_transient_for(parent)
    dialog.set_modal(False)
    dialog.set_hide_on_close(True)

    size = parent.get_size()
    width = int(size[0] / 3) if size[0] >= 1300 else int(size[0] / 2.3)
    dialog.set_default_size(width, -1)

    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    outer.set_margin_top(16)
    outer.set_margin_bottom(16)
    outer.set_margin_start(16)
    outer.set_margin_end(16)

    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    image = Gtk.Image.new_from_icon_name("dialog-warning")
    image.set_pixel_size(64)
    label1 = Gtk.Label(label=_("No Audio!!"))
    label1.add_css_class('label_extrabig')
    box.append(image)
    box.append(label1)
    outer.append(box)

    label2 = Gtk.Label(label=_("Pick up the microphone\nPress the mute button"))
    label2.set_justify(Gtk.Justification.CENTER)
    outer.append(label2)

    conf = context.get_conf()
    keep_closed_feature = conf.get_boolean('audio', 'keep_closed') or False
    buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    buttons.set_halign(Gtk.Align.END)
    if keep_closed_feature:
        keep_button = Gtk.Button(label=_("Keep Closed"))
        keep_button.connect("clicked", activate_hidden, dialog)
        buttons.append(keep_button)
    hide_button = Gtk.Button(label=_("Close"))
    hide_button.connect("clicked", lambda b: dialog.hide())
    buttons.append(hide_button)
    outer.append(buttons)

    dialog.set_child(outer)
    dialog.hide()
    return dialog
