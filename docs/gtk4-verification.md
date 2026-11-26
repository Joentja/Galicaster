# Verifying the GTK4 rebuild on an Ubuntu desktop

The GTK4 rebuild of the capture shell (PRs #1-#5) is verified headless in CI
(169 tests). This guide verifies it on a real Ubuntu desktop with a display,
audio and (optionally) capture hardware.

## 1. Install dependencies

Ubuntu 22.04 (jammy):

```bash
sudo apt update
sudo apt install python3-gi python3-dbus dbus-x11 gir1.2-gtk-4.0 \
  gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 \
  gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav \
  gstreamer1.0-alsa gstreamer1.0-pulseaudio
```

> **Note on live previews:** `gtk4paintablesink` comes from the
> `gstreamer1.0-gtk4` package, which is **not packaged on Ubuntu 22.04**
> (it exists on 23.10+/24.04). On 22.04 the app automatically falls back to
> `fakesink` for previews (recording still works fully). To test the actual
> on-screen preview, use Ubuntu 24.04 and additionally:
> `sudo apt install gstreamer1.0-gtk4`

Check: `gst-inspect-1.0 gtk4paintablesink` (only on 24.04+).

## 2. Run the unit tests with real GObject/GTK/GStreamer

```bash
cd /path/to/Galicaster
python3 -m unittest discover -s tests -t . -v   # or: nosetests3 --all-modules -a '!nodefault'
```

## 3. Launch the app

```bash
python3 run_galicaster.py
```

The default profile (`Default`, from `conf-dist.ini`) uses `videotest` +
`audiotest` sources, so it runs on any machine.

## 4. Functional checklist

- [ ] App starts fullscreen on GTK4 (`Gtk 4.0` loaded, no GTK3 errors in `logs/galicaster.log`)
- [ ] **Profile picker** (Profile button): switch between `Default`, `Test`, `Classroom`; tracks reload (previews re-created)
- [ ] **Monitoring**: two preview areas (on 24.04 with `gstreamer1.0-gtk4` you see moving test patterns; on 22.04 they stay black — expected fallback)
- [ ] **Audio meters**: the two audio sources show live L/R VU bars (audiotest tone/noise)
- [ ] **Input volume**: the sliders change the meter level live
- [ ] **Record**: REC starts recording (status pilot turns red), STOP finalizes; a new mediapackage appears under the repository folder with `mediapackage.xml` + track files
- [ ] **Recordings view** (Recordings button): lists the session; Play opens the player page with preview, seek bar, volume, VU meter; Edit metadata opens the editor; Ingest/Export/Delete work (Ingest needs a configured Opencast server in `conf.ini` `[ingest]`)
- [ ] **Events button**: shows upcoming scheduled events (requires Opencast `[ingest] active = True` with a reachable server; the scheduler pulls the agent's ical)
- [ ] **Opencast sync**: with `conf.ini` `[ingest]` configured, the strip shows Opencast Up/Down, scheduled events appear, recordings auto-start/stop at event times and ingest on stop

## 5. With real capture hardware

Use the `Classroom` profile (`profiles/classroom.ini`): two v4l2 devices
(`/dev/video0`, `/dev/video2`), each with its embedded audio. Adjust
`location`/`audiolocation` to your cards. Verify both previews show real
video and both meters move with real audio.

## 6. Automated smoke check

```bash
bash tools/verify_gtk4.sh
```

Runs import checks, pipeline construction with the Test profile, and a short
record/stop cycle headlessly (works without a display).
