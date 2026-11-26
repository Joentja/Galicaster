# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/classui/calendarwindow
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.
"""
Date/time picker dialog (GTK4, built in code)
"""

import datetime
import time
from gi.repository import Gtk

from galicaster.utils.i18n import _


class CalendarWindow:
    date = None

    def __init__(self, initial_value=0, parent_window=None):
        self.dialog = Gtk.Window(title=_("Select date"))
        if parent_window is not None:
            self.dialog.set_transient_for(parent_window)
        self.dialog.set_modal(True)
        self.dialog.set_hide_on_close(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        if not initial_value:
            now = time.localtime()
        else:
            now = initial_value.timetuple()
        year, month, day, hour, minute = now[0], now[1], now[2], now[3], now[4]

        self.calendar = Gtk.Calendar()
        self.calendar.select_month(month - 1, year)
        self.calendar.select_day(day)
        box.append(self.calendar)

        timebox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.hours = Gtk.SpinButton.new_with_range(0, 23, 1)
        self.hours.set_value(hour)
        self.minutes = Gtk.SpinButton.new_with_range(0, 59, 1)
        self.minutes.set_value(minute)
        timebox.append(Gtk.Label(label=_("Hour:")))
        timebox.append(self.hours)
        timebox.append(Gtk.Label(label=_("Minute:")))
        timebox.append(self.minutes)
        box.append(timebox)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        current = Gtk.Button(label=_("Current"))
        current.connect('clicked', self.do_select_current)
        none = Gtk.Button(label=_("None"))
        none.connect('clicked', self.do_select_none)
        ok = Gtk.Button(label=_("OK"))
        ok.connect('clicked', self.do_select_day)
        buttons.append(none)
        buttons.append(current)
        buttons.append(ok)
        box.append(buttons)

        self.dialog.set_child(box)
        self.dialog.connect('close-request', self.do_select_none)

    def run(self, data=None):
        self.dialog.present()
        return self.date

    def do_hide_calendar(self, calendarwindow):
        pass

    def do_select_current(self, button):
        self.date = datetime.datetime.now().replace(microsecond=0)
        self.dialog.close()

    def do_select_none(self, *args):
        self.date = None
        self.dialog.close()
        return True

    def do_select_day(self, button=None):
        date = self.calendar.get_date()
        hour = self.hours.get_value_as_int()
        minute = self.minutes.get_value_as_int()
        self.date = datetime.datetime(date.get_year(), date.get_month(), date.get_day_of_month(),
                                      hour, minute, 0)
        self.dialog.close()
