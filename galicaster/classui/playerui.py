# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/classui/playerui
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.
"""
Player area UI (GTK4, built in code): plays back a recorded mediapackage
with one Gtk.Picture per video source track, seek bar, volume, VU meter
and play/pause/stop controls.
"""

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gst

try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict

from galicaster.player import Player
from galicaster.core import context
from galicaster.classui import widget_children
from galicaster.utils.i18n import _

from galicaster.player.player import INIT
from galicaster.player.player import READY
from galicaster.player.player import PLAYING
from galicaster.player.player import PAUSED
from galicaster.player.player import STOPPED
from galicaster.player.player import ERRORED

log = context.get_logger()

PAGE_REC = 0
PAGE_MMA = 1
PAGE_PLA = 2


class PlayerClassUI(Gtk.Box):
    """
    Graphic User Interface for the player (GTK4)
    """
    __gtype_name__ = 'PlayerClass'

    def __init__(self, package=None):
        log.info("Creating Player Area (GTK4)")
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(6)
        self.set_margin_end(6)

        self.dispatcher = context.get_dispatcher()
        self.repo = context.get_repository()

        self.player = None
        self.mediapackage = None
        self.status = INIT
        self.previous = None
        self.duration = 0
        self.seeking = False
        self.rangeVum = 50
        self.stereo = True

        self.__build_topbar()
        self.__build_main_area()
        self.__build_controls()

        self.change_state(INIT)

        self.dispatcher.connect_ui("player-vumeter", self.set_vumeter)
        self.dispatcher.connect("player-status", self.change_state_bypass)
        self.dispatcher.connect_ui('play-list', self.play_from_list)
        self.dispatcher.connect_ui("view-changed", self.event_change_mode)
        self.dispatcher.connect_ui("quit", self.close)

    def __build_topbar(self):
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        back = Gtk.Button(label=_("Back to recordings"))
        back.connect('clicked', self.on_back)
        top.append(back)

        self.video_label = Gtk.Label(label="", xalign=0)
        self.video_label.add_css_class('dialog_title')
        top.append(self.video_label)

        self.presenter_label = Gtk.Label(label="", xalign=0)
        top.append(self.presenter_label)

        filler = Gtk.Box()
        filler.set_hexpand(True)
        top.append(filler)

        self.timer_label = Gtk.Label(label="")
        top.append(self.timer_label)

        self.append(top)

    def __build_main_area(self):
        middle = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        middle.set_vexpand(True)

        self.main_area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.main_area.set_hexpand(True)
        self.main_area.set_vexpand(True)
        self.main_area.add_css_class('videobox')
        middle.append(self.main_area)

        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        side.set_size_request(280, -1)

        self.vumeterL = Gtk.ProgressBar()
        self.vumeterR = Gtk.ProgressBar()
        bars = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.vumeterL.set_hexpand(True)
        self.vumeterR.set_hexpand(True)
        bars.append(self.vumeterL)
        bars.append(self.vumeterR)
        side.append(bars)
        self.channels_label = Gtk.Label(label=_("Stereo"), xalign=0)
        side.append(self.channels_label)

        vol_label = Gtk.Label(label=_("Volume"), xalign=0)
        side.append(vol_label)
        self.volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 1.0, 0.05)
        self.volume_scale.set_value(1.0)
        self.volume_scale.connect('value-changed', self.on_volume_changed)
        side.append(self.volume_scale)

        middle.append(side)
        self.append(middle)

    def __build_controls(self):
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls.set_halign(Gtk.Align.CENTER)

        self.seek_bar = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 100.0, 1.0)
        self.seek_bar.set_hexpand(True)
        self.seek_bar.connect('value-changed', self.on_seek)
        self.append(self.seek_bar)

        self.playbutton = Gtk.Button(label=_("Play"))
        self.playbutton.connect('clicked', self.on_play_clicked)
        controls.append(self.playbutton)

        self.pausebutton = Gtk.Button(label=_("Pause"))
        self.pausebutton.connect('clicked', self.on_pause_clicked)
        controls.append(self.pausebutton)

        self.stopbutton = Gtk.Button(label=_("Stop"))
        self.stopbutton.connect('clicked', self.on_stop_clicked)
        controls.append(self.stopbutton)

        self.append(controls)

    # ---- player lifecycle ----

    def init_player(self, element, mp):
        """Send absolute file names and Gtk.Picture widgets to the player."""
        if self.mediapackage != mp:
            if self.status == PAUSED:
                self.on_stop_clicked()

            self.mediapackage = mp

            tracks = OrderedDict()
            videos = OrderedDict()
            index = 0
            for t in mp.getTracks():
                flavor = t.getFlavor() or ""
                if flavor.count('other') or flavor.count("delivery") or flavor.count("composition"):
                    continue
                tracks[t.getIdentifier()] = t.getURI()
                if t.getMimeType() and t.getMimeType().count("video") and flavor.count("source"):
                    index += 1
                    videos[t.getIdentifier()] = index

            pictures = self.create_pictures(videos)

            self.seek_bar.set_value(0)
            if self.player:
                self.player.quit()

            self.player = Player(tracks, pictures)
            self.player.set_pictures(pictures)
            self.duration = self.player.get_duration()
            self.change_state(READY)

            self.video_label.set_text(self.mediapackage.title)
            self.presenter_label.set_text(self.mediapackage.getCreator() or "")

        self.on_play_clicked(None)

    def play_from_list(self, origin, package):
        """Takes a MP from the listing area and plays it"""
        self.dispatcher.emit("action-view-change", PAGE_PLA)
        self.init_player(None, package)

    def create_pictures(self, videos):
        """Create one Gtk.Picture per video source track of the mediapackage"""
        main = self.main_area
        for child in list(widget_children(main)):
            main.remove(child)

        pictures = OrderedDict()
        for track_id in videos:
            picture = Gtk.Picture()
            picture.set_name(track_id)
            picture.add_css_class('preview')
            picture.set_hexpand(True)
            picture.set_vexpand(True)
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            main.append(picture)
            pictures[track_id] = picture

        return pictures

    # ---- controls ----

    def on_play_clicked(self, button=None):
        self.change_state(PLAYING)
        self.player.play()
        self.__start_position_timer()
        return True

    def on_pause_clicked(self, button=None):
        self.player.pause()
        self.change_state(PAUSED)
        return True

    def on_stop_clicked(self, button=None):
        self.player.stop()
        self.seek_bar.set_value(0)
        self.set_timer(0, self.duration)
        self.change_state(STOPPED)
        return True

    def on_back(self, button):
        if self.status in (PLAYING, PAUSED):
            self.player.pause()
        self.dispatcher.emit("action-view-change", PAGE_MMA)

    def on_volume_changed(self, scale):
        if self.player:
            self.player.set_volume(scale.get_value())

    def on_seek(self, scale):
        if not self.player or not self.duration:
            return
        value = scale.get_value()
        if value > 100:
            value = 100
        self.seeking = True
        self.player.seek(value * self.duration * Gst.SECOND / 100.0, False)
        self.set_timer(value * self.duration / 100.0, self.duration)
        self.seeking = False

    # ---- timer / status ----

    def __start_position_timer(self):
        GObject.timeout_add(200, self.__update_position)

    def __update_position(self):
        if self.status not in (PLAYING, PAUSED) or not self.player:
            return False
        if not self.seeking:
            try:
                _, pos = self.player.get_position()
                timer = pos / Gst.SECOND
                if self.duration:
                    self.seek_bar.set_value(timer * 100.0 / self.duration)
                self.set_timer(timer, self.duration)
            except Exception:
                pass
        return True

    def set_timer(self, value, duration):
        self.timer_label.set_text(self.time_readable2(value, duration))

    def time_readable(self, seconds):
        iso = int(seconds)
        return "{}:{:02d}:{:02d}".format(iso // 3600, (iso % 3600) // 60, iso % 60)

    def time_readable2(self, s1, s2):
        return self.time_readable(s1) + " / " + self.time_readable(s2)

    def event_change_mode(self, orig, old_state, new_state):
        if old_state == PAGE_PLA and self.status == PLAYING:
            self.on_pause_clicked()

    def change_state_bypass(self, origin, state):
        self.change_state(state)
        return True

    def change_state(self, state):
        self.previous, self.status = self.status, state

        if state == INIT:
            sens = (False, False, False)
        elif state == READY:
            sens = (True, False, False)
        elif state == PLAYING:
            sens = (False, True, True)
        elif state == PAUSED:
            sens = (True, True, True)
        elif state == STOPPED:
            sens = (True, False, False)
        else:
            sens = (False, False, False)

        self.playbutton.set_sensitive(sens[0])
        self.pausebutton.set_sensitive(sens[1])
        self.stopbutton.set_sensitive(sens[2])

    def close(self, signal):
        if self.status in (PLAYING, PAUSED) and self.player:
            self.player.quit()
        return True

    # ---- audio meter ----

    def set_vumeter(self, element, data, data2, stereo):
        value, value2 = self.scale_data(data, data2)
        self.vumeterL.set_fraction(value)
        self.vumeterR.set_fraction(value2)

        if not stereo and self.stereo:
            self.stereo = False
            self.channels_label.set_text(_("Mono"))
        elif stereo and not self.stereo:
            self.stereo = True
            self.channels_label.set_text(_("Stereo"))

    def scale_data(self, data, data2):
        if data == "Inf":
            data = -200
        if data2 == "Inf":
            data2 = -200

        if data < -100:
            valor = 1
        else:
            valor = 1 - ((data + self.rangeVum) / float(self.rangeVum))

        if data2 < -100:
            valor2 = 1
        else:
            valor2 = 1 - ((data2 + self.rangeVum) / float(self.rangeVum))

        return valor, valor2

    def resize(self):
        return True


GObject.type_register(PlayerClassUI)
