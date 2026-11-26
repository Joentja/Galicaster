#!/usr/bin/env bash
# Headless smoke test for the GTK4 rebuild: imports, profile loading,
# pipeline construction and a short record/stop cycle with the Test profile.
# Usage: bash tools/verify_gtk4.sh   (run from the repo root on a machine with
# python3-gi, GTK4 and GStreamer installed)
set -u
cd "$(dirname "$0")/.."

echo "== 1. import check (Gtk 4.0, Gst 1.0) =="
python3 - <<'EOF'
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst
Gst.init(None)
print("Gtk", Gtk.get_major_version(), ".", Gtk.get_minor_version(), ".", Gtk.get_micro_version())
print("Gst", Gst.version_string())
sink = Gst.ElementFactory.find('gtk4paintablesink')
print("gtk4paintablesink:", "available" if sink else "NOT installed (previews fall back to fakesink)")
import galicaster.core.conf, galicaster.core.core, galicaster.recorder.service
import galicaster.classui.mainwindow, galicaster.classui.recorderui
import galicaster.classui.listing, galicaster.classui.playerui, galicaster.classui.metadata
print("all GTK4 modules import OK")
EOF
[ $? -eq 0 ] || { echo "IMPORT CHECK FAILED"; exit 1; }

echo "== 2. profile loading =="
python3 - <<'EOF'
from galicaster.core.conf import Conf
conf = Conf(conf_file='conf.ini', conf_dist_file='conf-dist.ini', profile_folder='profiles')
conf.reload()
for name, p in conf.get_profiles().items():
    print("profile:", name, "->", [(t.name, t.device, t.flavor) for t in p.tracks])
conf.change_current_profile('Test')
print("current:", conf.get_current_profile().name)
EOF
[ $? -eq 0 ] || { echo "PROFILE CHECK FAILED"; exit 1; }

echo "== 3. short record/stop cycle with the Test profile (headless, fakesink previews) =="
python3 - <<'EOF'
import time, tempfile, os
from gi.repository import Gst
Gst.init(None)
from galicaster.core import context
conf = context.get_conf()
conf.reload()
conf.change_current_profile('Test')
repo = context.get_repository()
tmp = tempfile.mkdtemp(prefix='gc-verify-')
repo.root = tmp
repo.create_repo(conf.get_hostname())
os.chdir(repo.get_rectemp_path())
from galicaster.core.dispatcher import Dispatcher
from galicaster.recorder.service import RecorderService
d = context.get_dispatcher()
rec = RecorderService(d, repo, None, conf, context.get_logger())
profile = conf.get_current_profile()
bins = profile.get_tracks_audio_at_end()
for b in bins:
    b['path'] = repo.get_rectemp_path()
from galicaster.recorder.recorder import Recorder
rec.recorder = Recorder(bins)
rec.recorder.preview()
mp = rec.create_mp()
rec.record(mp)
time.sleep(5)
rec.stop()
mp_dir = os.path.join(tmp, mp.getIdentifier())
assert os.path.isdir(mp_dir), "mediapackage folder missing"
files = sorted(os.listdir(mp_dir))
print("recorded files:", files)
assert any(f.endswith('.avi') for f in files), "no video track file"
assert 'mediapackage.xml' in files or any(f.endswith('.xml') for f in files), "no manifest"
print("RECORD/STOP CYCLE OK")
EOF
[ $? -eq 0 ] || { echo "RECORD CYCLE FAILED"; exit 1; }

echo "ALL CHECKS PASSED"
