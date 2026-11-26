# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/player/player
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.

import gi

gi.require_version("Gst", "1.0")

from gi.repository import Gst, GObject

import os

from galicaster.core import context
from galicaster.utils.gstreamer import WeakMethod
from galicaster.utils.mediainfo import get_duration

logger = context.get_logger()

GST_TIMEOUT = Gst.SECOND * 10

INIT    = 0
READY   = 1
PLAYING = 2
PAUSED  = 3
STOPPED = 4
ERRORED = 5


class Player(object):
    def __init__(self, files, players={}):
        """
        Initialize the player.
        This class is event-based and needs a mainloop to work properly.

        :param files: a ``dict`` mapping track identifiers to file paths to play
        :param players: a ``dict`` mapping track identifiers to Gtk.Picture widgets
        """
        if not isinstance(files, dict):
            raise TypeError(
                '%s: need a %r; got a %r: %r' % ('files', dict, type(files), files)
            )
        if not isinstance(players, dict):
            raise TypeError(
                '%s: need a %r; got a %r: %r' % ('players', dict, type(players), players)
            )

        self.dispatcher = context.get_dispatcher()
        self.files = files
        self.players = players
        self.duration = 0
        self.has_audio = False
        self.error = None
        self.pipeline_complete = False
        self.pipeline = None
        self.audio_sink = None

        self.__get_duration_and_run()

    def __del__(self):
        if self.pipeline:
            self.pipeline.get_bus().remove_signal_watch()

    def create_pipeline(self):
        self.pipeline = Gst.Pipeline.new("galicaster_player")
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message::eos', WeakMethod(self, '_on_eos'))
        bus.connect('message::error', WeakMethod(self, '_on_error'))
        bus.connect('message::element', WeakMethod(self, '_on_message_element'))
        bus.connect('message::state-changed', WeakMethod(self, '_on_state_changed'))

        for name, location in list(self.files.items()):
            logger.info('playing %r', location)
            src = Gst.ElementFactory.make('filesrc', 'src-' + name)
            src.set_property('location', location)
            dec = Gst.ElementFactory.make('decodebin', 'decode-' + name)
            dec.connect('pad-added', WeakMethod(self, '_on_new_decoded_pad'))

            self.pipeline.add(src)
            self.pipeline.add(dec)
            src.link(dec)

        self.error = None
        return None

    def set_pictures(self, pictures):
        """Bind Gtk.Picture widgets to the video sinks of the pipeline.

        :param pictures: ``dict`` mapping track identifiers to Gtk.Picture widgets
        """
        self.players = pictures
        if self.pipeline is None:
            return
        for name, picture in list(pictures.items()):
            sink = self.pipeline.get_by_name('sink-' + name)
            if sink is not None:
                self.__bind_paintable(name, sink, picture)

    def __bind_paintable(self, name, sink, picture):
        def on_notify(sink, param):
            paintable = sink.get_property('paintable')
            if paintable is not None:
                picture.set_paintable(paintable)
                sink.disconnect_by_func(on_notify)

        paintable = sink.get_property('paintable')
        if paintable is not None:
            picture.set_paintable(paintable)
        else:
            sink.connect('notify::paintable', on_notify)

    def get_status(self, timeout=GST_TIMEOUT):
        """Get the player status"""
        status = self.pipeline.get_state(timeout)

        if status[0] == Gst.StateChangeReturn.ASYNC:
            logger.error('Timeout getting player status, current status: {}'.format(status))

        return status

    def is_playing(self):
        """Get True if is playing else False"""
        return (self.get_status()[1] == Gst.State.PLAYING)

    def get_time(self):
        """Get the player current time."""
        try:
            clock = self.pipeline.get_clock()
            if clock:
                return clock.get_time()
        except Exception:
            pass

        return 0

    def play(self):
        """Start to play"""
        logger.info("Player playing")
        if not self.pipeline_complete:
            self.pipeline.set_state(Gst.State.PAUSED)
            self.pipeline_complete = True
        else:
            self.dispatcher.emit("player-status", PLAYING)
            self.pipeline.set_state(Gst.State.PLAYING)
        return None

    def pause(self):
        """Pause the player"""
        logger.info("Player paused")
        self.pipeline.set_state(Gst.State.PAUSED)
        self.dispatcher.emit("player-status", PAUSED)
        self.get_status()

    def stop(self):
        """Stop the player: pause and seek to the beginning"""
        logger.info("Player stopped")
        self.pipeline.set_state(Gst.State.PAUSED)
        self.seek(0)
        self.dispatcher.emit("player-status", STOPPED)
        self.get_status()
        return None

    def quit(self):
        """Close the pipeline"""
        logger.info("Player deleted")
        self.pipeline.set_state(Gst.State.NULL)
        self.dispatcher.emit("player-status", STOPPED)
        self.get_status()
        return None

    def seek(self, pos, recover_state=False):
        """Seek the player. pos is a time in nanoseconds."""
        result = self.pipeline.seek(1.0,
                                    Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                                    Gst.SeekType.SET, pos,
                                    Gst.SeekType.NONE, -1)
        if recover_state and self.get_status()[1] == Gst.State.PAUSED:
            self.pipeline.set_state(Gst.State.PLAYING)
            self.dispatcher.emit("player-status", PLAYING)
        return result

    def get_duration(self):
        return self.duration

    def get_position(self, format=Gst.Format.TIME):
        return self.pipeline.query_position(format)

    def get_volume(self):
        if self.audio_sink is None:
            return 100
        return self.audio_sink.get_property('volume')

    def set_volume(self, volume):
        if self.audio_sink is not None:
            self.audio_sink.set_property('volume', volume)

    def _on_state_changed(self, bus, message):
        old, new, pending = message.parse_state_changed()
        if (isinstance(message.src, Gst.Pipeline) and
                    (old, new) == (Gst.State.READY, Gst.State.PAUSED)):
            self.pipeline.set_state(Gst.State.PLAYING)

    def _on_new_decoded_pad(self, element, pad):
        name = pad.query_caps(None).to_string()
        element_name = element.get_name()[7:]
        logger.info('new decoded pad: %r in %r', name, element_name)

        if self.error:
            logger.warning('There was an error, the decoded pad will be ignored: %r in %r', name, element_name)
            return None

        if name.startswith('audio/'):
            if not self.has_audio:
                self.has_audio = True
                audioconvert = Gst.ElementFactory.make('audioconvert', 'audioconvert')
                self.pipeline.add(audioconvert)
                pad.link(audioconvert.get_static_pad('sink'))
                audioconvert.set_state(Gst.State.PAUSED)

                vumeter = Gst.ElementFactory.make('level', 'level')
                vumeter.set_property('message', True)
                vumeter.set_property('interval', 100000000)
                self.pipeline.add(vumeter)
                audioconvert.link(vumeter)
                vumeter.set_state(Gst.State.PAUSED)

                self.audio_sink = Gst.ElementFactory.make('autoaudiosink', 'audio')
                self.pipeline.add(self.audio_sink)
                vumeter.link(self.audio_sink)
                assert self.audio_sink.set_state(Gst.State.PAUSED)

        elif name.startswith('video/'):
            vconvert = Gst.ElementFactory.make('videoconvert', 'vconvert-' + element_name)
            self.pipeline.add(vconvert)

            if Gst.ElementFactory.find('gtk4paintablesink') is not None:
                sink = Gst.ElementFactory.make('gtk4paintablesink', 'sink-' + element_name)
            else:
                logger.warning("gtk4paintablesink not available, using fakesink for playback of %r", element_name)
                sink = Gst.ElementFactory.make('fakesink', 'sink-' + element_name)
            sink.set_property('force-aspect-ratio', True)
            self.pipeline.add(sink)

            pad.link(vconvert.get_static_pad('sink'))
            vconvert.link(sink)
            vconvert.set_state(Gst.State.PAUSED)
            assert sink.set_state(Gst.State.PAUSED)

            if element_name in self.players:
                GObject.idle_add(self.__bind_paintable, element_name, sink, self.players[element_name])

        return None

    def _on_eos(self, bus, msg):
        logger.info('Player EOS')
        self.stop()
        self.dispatcher.emit("player-status", STOPPED)

    def _on_error(self, bus, msg):
        self.error = msg.parse_error()[1]
        logger.error(self.error)
        self.dispatcher.emit("player-status", ERRORED)
        self.quit()

    def _on_message_element(self, bus, message):
        if message.get_structure().get_name() == 'level':
            self.__set_vumeter(message)

    def __set_vumeter(self, message):
        struct = message.get_structure()
        rms_values = struct.get_value('rms')
        stereo = False
        valor = "Inf"
        valor2 = valor

        if len(rms_values) > 0 and float(rms_values[0]) != float("-inf"):
            valor = float(rms_values[0])
            valor2 = valor

        if len(rms_values) > 1:
            stereo = True
            valor2 = "Inf"
            if float(rms_values[1]) != float("-inf"):
                valor2 = float(rms_values[1])

        self.dispatcher.emit("player-vumeter", valor, valor2, stereo)

    def __discover(self, filepath):
        self.duration = 0
        try:
            self.duration = get_duration(filepath)
            logger.info("Duration ON_DISCOVERED: " + str(self.duration))
        except Exception as exc:
            logger.warning("Error trying to get duration of {}: {}".format(filepath, exc))

        self.create_pipeline()
        return True

    def __get_duration_and_run(self):
        minsize = location = None
        for key, value in list(self.files.items()):
            size = os.path.getsize(value)
            if not minsize or size < minsize:
                minsize = size
                location = value
        return self.__discover(location)
