# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/classui/recorderui
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.
"""
Recording Area GUI (GTK4, built in code)

Shows a live preview of every video source of the current profile, one VU
meter and one input-volume slider per audio source, the recorder controls
and the next scheduled event.
"""

import datetime

from gi.repository import GObject
from gi.repository import Gtk, GLib

from galicaster.core import context
from galicaster.classui import message, widget_children
from galicaster.classui.profile import ProfileDialog
from galicaster.utils import readable
from galicaster.utils.resize import relabel
from galicaster.utils.i18n import _

from galicaster.recorder.service import STATUSES
from galicaster.recorder.service import INIT_STATUS
from galicaster.recorder.service import PREVIEW_STATUS
from galicaster.recorder.service import RECORDING_STATUS
from galicaster.recorder.service import PAUSED_STATUS
from galicaster.recorder.service import ERROR_STATUS

from collections import OrderedDict

logger = context.get_logger()
status_label_changed = True
status_label_blink = True
signalized = False

NEXT_TEXT = _("Upcoming")
CURRENT_TEXT = _("Current")

TIME_BLINK_START = 20
TIME_BLINK_STOP = 20
TIME_RED_START = 50
TIME_RED_STOP = 50
TIME_UPCOMING = 60

PAGE_REC = 0
PAGE_MMA = 1


class RecorderClassUI(Gtk.Box):
    """
    Graphic User Interface for the recorder (GTK4)
    """

    __gtype_name__ = 'RecorderClass'

    def __init__(self, package=None):
        logger.info("Creating Recording Area (GTK4)")
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(6)
        self.set_margin_end(6)

        self.repo = context.get_repository()
        self.dispatcher = context.get_dispatcher()
        self.worker = context.get_worker()
        self.conf = context.get_conf()
        self.recorder = context.get_recorder()
        self.recorder.set_create_pictures_func(self.create_pictures)

        self.rangeVum = 50
        self.thresholdVum = self.conf.get_float('audio', 'min')
        self.mute = False
        self.low_audio = False
        self.lowaudio_threshold = self.conf.get_float('lowaudio', 'lowaudio_threshold')

        self.swap = False
        self.focus_is_active = False
        self.error_dialog = None
        self.pause_dialog = None
        self.profile_dialog = None

        self.meters = {}
        self.volumes = {}

        self.allow_pause = self.conf.get_permission("pause")
        self.allow_start = self.conf.get_permission("start")
        self.allow_stop = self.conf.get_permission("stop")
        self.allow_manual = self.conf.get_permission("manual")
        self.allow_overlap = self.conf.get_permission("overlap")

        self.help_main_str = self.conf.get('help', 'main')
        self.help_text_str = self.conf.get('help', 'text')

        self.__build_topbar()
        self.__build_main_area()
        self.__build_side_panel()

        self.dispatcher.connect_ui("init", self.check_status_area)
        self.dispatcher.connect_ui("init", self.check_net, None)
        self.dispatcher.connect_ui("opencast-status", self.check_net)
        self.dispatcher.connect_ui("recorder-vumeter", self.set_vumeter)
        self.dispatcher.connect_ui("view-changed", self.event_change_mode)
        self.dispatcher.connect_ui("recorder-status", self.handle_status)
        self.dispatcher.connect_ui("recorder-ready", self.build_audio_controls)
        self.dispatcher.connect_ui("recorder-ready", self.reset_mute)

        deps = (self.eventlabel, self.nextlabel, self.titlelabel)
        GObject.timeout_add(500, self.update_scheduler_timeout, *deps)
        GObject.timeout_add(10000, self.update_clock_timeout)
        self.update_clock_timeout()

    # ---- UI construction ----

    def __build_topbar(self):
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)

        self.status_view = Gtk.Label()
        self.status_view.add_css_class('label_extrabig')
        top.append(self.status_view)

        self.nextlabel = Gtk.Label(label="")
        self.titlelabel = Gtk.Label(label=_("No upcoming events"))
        self.eventlabel = Gtk.Label(label="")
        top.append(self.nextlabel)
        top.append(self.titlelabel)
        top.append(self.eventlabel)

        self.clock = Gtk.Label()
        top.append(self.clock)

        filler = Gtk.Box()
        filler.set_hexpand(True)
        top.append(filler)

        profile_button = Gtk.Button(label=_("Profile"))
        profile_button.connect('clicked', self.on_profile)
        top.append(profile_button)

        events_button = Gtk.Button(label=_("Events"))
        events_button.connect('clicked', self.show_next)
        top.append(events_button)

        self.editbutton = Gtk.Button(label=_("Edit"))
        self.editbutton.connect('clicked', self.on_edit_meta)
        top.append(self.editbutton)

        mma_button = Gtk.Button(label=_("Recordings"))
        mma_button.connect('clicked', self.change_mode)
        top.append(mma_button)

        help_button = Gtk.Button(label=_("Help"))
        help_button.connect('clicked', self.on_help)
        top.append(help_button)

        self.append(top)

    def __build_main_area(self):
        middle = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        middle.set_vexpand(True)

        self.main_area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.main_area.set_hexpand(True)
        self.main_area.set_vexpand(True)
        self.main_area.add_css_class('videobox')
        middle.append(self.main_area)

        self.side_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.side_panel.set_size_request(280, -1)
        middle.append(self.side_panel)

        self.append(middle)

    def __build_side_panel(self):
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        controls.set_halign(Gtk.Align.CENTER)

        self.recbutton = Gtk.Button(label=_("REC"))
        self.recbutton.add_css_class('rec_button')
        self.recbutton.connect('clicked', self.on_rec)
        controls.append(self.recbutton)

        self.pausebutton = Gtk.Button(label=_("Pause"))
        self.pausebutton.connect('clicked', self.on_pause)
        controls.append(self.pausebutton)

        self.stopbutton = Gtk.Button(label=_("Stop"))
        self.stopbutton.connect('clicked', self.on_ask_stop)
        controls.append(self.stopbutton)

        self.side_panel.append(controls)

        self.recording_title = Gtk.Label(label=_("Not recording"), wrap=True)
        self.recording_elapsed = Gtk.Label(label="")
        self.side_panel.append(self.recording_title)
        self.side_panel.append(self.recording_elapsed)

        self.audio_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.side_panel.append(self.audio_box)

        self.tools_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.side_panel.append(self.tools_box)

    def add_tool(self, widget):
        """Append a widget (e.g. from a plugin) to the side panel"""
        self.tools_box.append(widget)

    # ---- previews ----

    def create_pictures(self, sources):
        """Create one Gtk.Picture per video source and return them by sink name"""
        main = self.main_area

        if self.swap:
            sources = list(reversed(sources))

        for child in list(widget_children(main)):
            main.remove(child)

        pictures = OrderedDict()
        for source in sources:
            picture = Gtk.Picture()
            picture.set_name(source)
            picture.add_css_class('preview')
            picture.set_hexpand(True)
            picture.set_vexpand(True)
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            main.append(picture)
            pictures[source] = picture

        return pictures

    # ---- audio meters and volume ----

    def build_audio_controls(self, element=None):
        for child in list(widget_children(self.audio_box)):
            self.audio_box.remove(child)
        self.meters = {}
        self.volumes = {}

        for name in self.recorder.get_audio_bins():
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.add_css_class('audio_source')

            label = Gtk.Label(label=name, xalign=0)
            label.add_css_class('audio_source_name')
            box.append(label)

            bars = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            bar_l = Gtk.ProgressBar()
            bar_r = Gtk.ProgressBar()
            bar_l.set_hexpand(True)
            bar_r.set_hexpand(True)
            bars.append(bar_l)
            bars.append(bar_r)
            box.append(bars)
            self.meters[name] = (bar_l, bar_r)

            vol_label = Gtk.Label(label=_("Input volume"), xalign=0)
            box.append(vol_label)
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 2.0, 0.05)
            current = self.recorder.get_input_volume(name)
            scale.set_value(current if current is not None else 1.0)
            scale.connect('value-changed', self.on_volume_changed, name)
            box.append(scale)
            self.volumes[name] = scale

            self.audio_box.append(box)

    def on_volume_changed(self, scale, name):
        self.recorder.set_input_volume(name, scale.get_value())

    def set_vumeter(self, element, bin_name, data, data2, stereo):
        if bin_name not in self.meters:
            return
        value, value2 = self.scale_data(data, data2)
        bar_l, bar_r = self.meters[bin_name]
        bar_l.set_fraction(value)
        bar_r.set_fraction(value2)

    def clear_vumeter(self):
        for bar_l, bar_r in self.meters.values():
            bar_l.set_fraction(0)
            bar_r.set_fraction(0)

    def scale_data(self, data, data2):
        if data == "Inf":
            data = -200
        if data2 == "Inf":
            data2 = -200

        average = (data + data2) / 2.0
        if not self.mute:
            if self.lowaudio_threshold and average < (self.lowaudio_threshold):
                self.dispatcher.emit("low-audio")
                self.low_audio = True
            if average < (self.thresholdVum):
                self.dispatcher.emit("audio-mute")
                self.mute = True
        if self.mute and average > (self.thresholdVum + 5.0):
            self.dispatcher.emit("audio-recovered")
            self.mute = False
        if self.low_audio and self.lowaudio_threshold and average > (self.lowaudio_threshold + 5.0):
            self.dispatcher.emit("low-audio-recovered")
            self.low_audio = False

        if data < -self.rangeVum:
            valor = 1
        else:
            valor = 1 - ((data + self.rangeVum) / float(self.rangeVum))

        if data2 < -self.rangeVum:
            valor2 = 1
        else:
            valor2 = 1 - ((data2 + self.rangeVum) / float(self.rangeVum))

        return valor, valor2

    # ---- controls ----

    def on_rec(self, button=None):
        logger.info("Recording")
        self.recorder.record()

    def on_pause(self, button):
        if self.recorder.status == PAUSED_STATUS:
            self.dispatcher.emit("action-audio-enable-msg")
            logger.debug("Resuming Recording")
            self.recorder.resume()
        elif self.recorder.status == RECORDING_STATUS:
            self.dispatcher.emit("action-audio-disable-msg")
            logger.debug("Pausing Recording")
            self.recorder.pause()

    def on_ask_stop(self, button):
        if self.conf.get_boolean("basic", "stopdialog"):
            text = {"title": _("Recorder"),
                    "main": _("Are you sure you want to\nstop the recording?")}
            buttons = (("_Stop", Gtk.ResponseType.OK), ("_Cancel", Gtk.ResponseType.REJECT))
            message.PopUp(message.WARN_STOP, text,
                          context.get_mainwindow(), buttons, self.on_stop_dialog_response)
        else:
            self.recorder.stop()

    def on_stop_dialog_response(self, response_id, **kwargs):
        if response_id in message.POSITIVE:
            self.recorder.stop()

    def on_help(self, button):
        logger.info("Help requested")
        text = {"title": _("Help"),
                "main": _(self.help_main_str),
                "text": _(self.help_text_str)
                }
        message.PopUp(message.INFO, text, context.get_mainwindow())

    def on_profile(self, button):
        if self.profile_dialog is None:
            self.profile_dialog = ProfileDialog(parent=context.get_mainwindow())
        self.profile_dialog.present()

    def on_edit_meta(self, button):
        from galicaster.classui.metadata import MetadataClass
        if self.recorder.current_mediapackage and self.recorder.current_mediapackage.manual:
            MetadataClass(self.recorder.current_mediapackage, parent=context.get_mainwindow())

    def show_next(self, button=None):
        mps = self.repo.get_next_mediapackages(5)
        next_recs = []
        for mp in mps:
            rec_time = mp.getLocalDate()
            if rec_time.date() == datetime.date.today():
                date = _("Today")
            elif rec_time.date() == (datetime.date.today() + datetime.timedelta(1)):
                date = _("Tomorrow")
            else:
                date = mp.getDate().strftime("%d %b %Y")
            next_recs.append({'title': mp.title,
                              'date': date,
                              'duration': rec_time.time().strftime("%H:%M")})
        text = {'title': _('Next Recordings'), 'next_recs': next_recs}
        message.PopUp(message.NEXT_REC, text, context.get_mainwindow())

    def change_mode(self, button):
        """GUI callback: switch to the recordings (media manager) page"""
        self.dispatcher.emit("action-view-change", PAGE_MMA)

    def launch_error_message(self, error_msg=None):
        msg = error_msg or self.recorder.error_msg
        text = {
            "title": _("Recorder"),
            "main": _(" Please review your configuration \nor load another profile"),
            "text": msg
        }
        if self.error_dialog:
            self.destroy_error_dialog()
        self.error_dialog = message.PopUp(message.ERROR, text,
                                          context.get_mainwindow(), None, self.on_close_error_affirmative)

    def on_close_error_affirmative(self, origin=None, **kwargs):
        self.dispatcher.emit("action-reload-profile")

    def destroy_error_dialog(self):
        if self.error_dialog:
            self.error_dialog.dialog_destroy()
            self.error_dialog = None

    # ---- status and info ----

    def recording_info_timeout(self):
        if self.recorder.status in [PAUSED_STATUS, RECORDING_STATUS] and self.recorder.current_mediapackage:
            self.recording_title.set_text(self.recorder.current_mediapackage.getTitle())
            msec = datetime.timedelta(microseconds=(round(self.recorder.get_recorded_time() / 1000.0, -6)))
            self.recording_elapsed.set_text(_("Elapsed Time: ") + readable.long_time(msec))
            return True
        self.recording_title.set_text(_("Not recording"))
        self.recording_elapsed.set_text("")
        return True

    def update_clock_timeout(self):
        self.clock.set_text(datetime.datetime.now().time().strftime("%H:%M"))
        return True

    def update_scheduler_timeout(self, status, event_type, title):
        """GObject.timeout callback with 500 ms intervals"""
        global status_label_changed, status_label_blink, signalized

        if self.recorder.current_mediapackage and not self.recorder.current_mediapackage.manual:
            start = self.recorder.current_mediapackage.getLocalDate()
            duration = self.recorder.current_mediapackage.getDuration() / 1000
            end = start + datetime.timedelta(seconds=duration)
            dif = end - datetime.datetime.now()

            if dif < datetime.timedelta(0):
                return True

            if self.recorder.current_mediapackage.anticipated:
                status.set_text("")
                event_type.set_text(CURRENT_TEXT)
                title.set_text(self.recorder.current_mediapackage.title)
                return True
            status.set_text(_("Stopping in {0}").format(readable.long_time(dif)))
            event_type.set_text(CURRENT_TEXT)
            title.set_text(self.recorder.current_mediapackage.title)

            if dif < datetime.timedelta(0, TIME_RED_STOP):
                if not status_label_changed:
                    status.set_css_classes(['red_coloured'])
                    status_label_changed = True
            elif status_label_changed:
                status.set_css_classes(['black_coloured'])
                status_label_changed = False
            if dif < datetime.timedelta(0, TIME_BLINK_STOP):
                if status_label_blink:
                    status.set_css_classes(['blinking_coloured_from'])
                else:
                    status.set_css_classes(['blinking_coloured_to'])
                status_label_blink = not status_label_blink

        else:
            next_mediapackage = self.repo.get_next_mediapackage()
            if next_mediapackage and next_mediapackage.isScheduled():
                start = next_mediapackage.getLocalDate()
                dif = start - datetime.datetime.now()
                event_type.set_text(NEXT_TEXT)
                title.set_text(next_mediapackage.title)
                status.set_text(_("Starting in {0}").format(readable.long_time(dif)))

                if dif < datetime.timedelta(0, TIME_UPCOMING):
                    if not signalized:
                        self.dispatcher.emit("recorder-upcoming-event")
                    signalized = True
                elif signalized:
                    signalized = False

                if dif < datetime.timedelta(0, TIME_RED_START):
                    if not status_label_changed:
                        status.set_css_classes(['red_coloured'])
                        status_label_changed = True
                    elif status_label_changed:
                        status.set_css_classes(['black_coloured'])
                        status_label_changed = False

                if dif < datetime.timedelta(0, TIME_BLINK_START):
                    if status_label_blink:
                        status.set_css_classes(['blinking_coloured_from'])
                    else:
                        status.set_css_classes(['blinking_coloured_to'])
                    status_label_blink = not status_label_blink

            else:
                if event_type.get_text():
                    event_type.set_text("")
                if status.get_text():
                    status.set_text("")
                title.set_text(_("No upcoming events"))

        return True

    def check_status_area(self, origin, signal=None, other=None):
        self.recording_title.set_text(_("Idle"))

    def check_net(self, origin, status=None):
        pass

    def handle_status(self, origin, status):
        """Activates or deactivates the buttons depending on the new status"""
        if status == INIT_STATUS:
            self.recbutton.set_sensitive(False)
            self.pausebutton.set_sensitive(False)
            self.stopbutton.set_sensitive(False)

        elif status == PREVIEW_STATUS:
            self.recbutton.set_sensitive(bool(self.allow_start or self.allow_manual))
            self.pausebutton.set_sensitive(False)
            self.stopbutton.set_sensitive(False)
            self.editbutton.set_sensitive(False)

        elif status == RECORDING_STATUS:
            GObject.timeout_add(500, self.recording_info_timeout)
            self.recbutton.set_sensitive(False)
            self.pausebutton.set_sensitive(bool(self.allow_pause and self.recorder.is_pausable()))
            self.stopbutton.set_sensitive(bool(self.allow_stop or self.allow_manual))
            self.editbutton.set_sensitive(bool(self.recorder.current_mediapackage
                                             and self.recorder.current_mediapackage.manual))

        elif status == PAUSED_STATUS:
            self.recbutton.set_sensitive(False)
            self.pausebutton.set_sensitive(True)
            self.stopbutton.set_sensitive(bool(self.allow_stop or self.allow_manual))

        elif status == ERROR_STATUS:
            self.recbutton.set_sensitive(False)
            self.pausebutton.set_sensitive(False)
            self.stopbutton.set_sensitive(False)
            if self.focus_is_active:
                self.launch_error_message()

        if status in STATUSES:
            self.status_view.set_text(_(status.description))
            css = ['status_pilot']
            if status.bg_color:
                css.append('red_coloured')
            self.status_view.set_css_classes(css)
        else:
            logger.error("Unable to change status label, unknown status {}".format(status))

        if status not in [ERROR_STATUS] and self.error_dialog:
            self.destroy_error_dialog()

    def event_change_mode(self, orig, old_state, new_state):
        """Handles the focus of the Recording Area"""
        if new_state == PAGE_REC:
            self.focus_is_active = True
            self.recorder.mute_preview(False)
            if self.recorder.status == ERROR_STATUS:
                self.launch_error_message()
        if old_state == PAGE_REC:
            self.focus_is_active = False
            self.recorder.mute_preview(True)

    def block(self):
        self.focus_is_active = True
        self.recorder.mute_preview(False)

    def reset_mute(self, element):
        self.mute = False

    def resize(self):
        size = context.get_mainwindow().get_size()
        k1 = size[0] / 1920.0
        relabel(self.clock, k1 * 25, False)
        relabel(self.nextlabel, k1 * 25, True)
        relabel(self.titlelabel, k1 * 33, True)
        relabel(self.recording_title, k1 * 25, True)
        return True


GObject.type_register(RecorderClassUI)
