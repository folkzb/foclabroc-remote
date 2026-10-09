"""Exercise the embedded uinput protocol without root or Batocera hardware."""
import json
import os
from pathlib import Path
import re
import select
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVDEV_STUB = '''
import json, os
class Codes:
    def __getattr__(self, name): return name
ecodes = Codes()
def AbsInfo(*args): return args
class UInput:
    def __init__(self, capabilities, **kwargs):
        self.log = open(os.environ["VPAD_TEST_LOG"], "w", buffering=1)
        self.log.write(json.dumps(["device", capabilities, kwargs]) + "\\n")
    def write(self, kind, code, value):
        self.log.write(json.dumps([kind, code, value]) + "\\n")
    def syn(self): pass
    def close(self):
        self.log.write(json.dumps(["closed"]) + "\\n")
        self.log.close()
'''

class ProtocolTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        (self.base / "evdev.py").write_text(EVDEV_STUB)
        self.processes = []
        self.addCleanup(self.cleanup_processes)

    def cleanup_processes(self):
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=3)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream:
                    stream.close()

    def start(self, path):
        source = (ROOT / path).read_text()
        script = re.search(r"const _padScript = r'''(.*?)''';", source, re.S).group(1)
        compile(script, path, "exec")
        script_path = self.base / "pad.py"
        script_path.write_text(script)
        log = self.base / ("events" + str(len(self.processes)) + ".jsonl")
        env = dict(os.environ, VPAD_TEST_LOG=str(log), PYTHONPATH=str(self.base))
        process = subprocess.Popen([sys.executable, "-u", str(script_path)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        self.processes.append(process)
        self.assertTrue(select.select([process.stdout], [], [], 3)[0], "Missing READY")
        self.assertEqual(process.stdout.readline(), b"READY\n")
        return process, log

    def events(self, log):
        return [json.loads(line) for line in log.read_text().splitlines()]

    def send(self, process, command):
        process.stdin.write((command + "\n").encode())
        process.stdin.flush()

    def wait_event(self, log, event, timeout=1):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if event in self.events(log):
                return
            time.sleep(0.01)
        self.fail(f"Missing event {event}; got {self.events(log)}")

    def test_axes_dpad_and_neutral_cleanup_for_both_languages(self):
        for path in ("lib/screens/virtual_pad_screen.dart",
                     "batocera_remote_en/lib/screens/virtual_pad_screen.dart"):
            with self.subTest(path=path):
                p, log = self.start(path)
                device = self.events(log)[0]
                self.assertEqual(device[2]["vendor"], 0x045e)
                self.assertEqual(device[2]["product"], 0x028e)
                axes = dict(device[1]["EV_ABS"])
                self.assertEqual(axes["ABS_RX"][1:3], [-32768, 32767])
                self.send(p, "stick left 16000 -8000\nstick right 99999 -99999\npress l3\npress left\npress right\nrelease right")
                self.wait_event(log, ["EV_ABS", "ABS_HAT0X", -1])
                self.wait_event(log, ["EV_ABS", "ABS_RY", -32768])
                events = self.events(log)
                self.assertIn(["EV_ABS", "ABS_X", 16000], events)
                self.assertIn(["EV_ABS", "ABS_Y", -8000], events)
                self.assertIn(["EV_ABS", "ABS_RX", 32767], events)
                self.assertIn(["EV_KEY", "BTN_THUMBL", 1], events)
                self.send(p, "quit")
                self.assertEqual(p.wait(timeout=3), 0)
                events = self.events(log)
                for axis in ("ABS_X", "ABS_Y", "ABS_RX", "ABS_RY", "ABS_HAT0X", "ABS_HAT0Y"):
                    self.assertEqual([x[2] for x in events if len(x) == 3 and x[1] == axis][-1], 0)
                self.assertEqual(events[-1], ["closed"])

    def test_invalid_commands_do_not_kill_controller(self):
        p, log = self.start("lib/screens/virtual_pad_screen.dart")
        self.send(p, "stick left nope 100\nstick other 1 2\ninvalid a\npress a")
        self.wait_event(log, ["EV_KEY", "BTN_A", 1])
        self.assertIsNone(p.poll())
        self.send(p, "reset")
        self.wait_event(log, ["EV_KEY", "BTN_A", 0])

    def test_watchdog_releases_controls_when_heartbeat_stops(self):
        p, log = self.start("lib/screens/virtual_pad_screen.dart")
        self.send(p, "press a\nstick left 20000 10000")
        self.wait_event(log, ["EV_KEY", "BTN_A", 1])
        # Heartbeats preserve a legitimately held button.
        for _ in range(3):
            self.send(p, "ping")
            time.sleep(0.2)
        self.assertNotIn(["EV_KEY", "BTN_A", 0], self.events(log))
        self.wait_event(log, ["EV_KEY", "BTN_A", 0], timeout=3)
        self.wait_event(log, ["EV_ABS", "ABS_X", 0])

    def test_eof_closes_device_and_releases_controls(self):
        p, log = self.start("lib/screens/virtual_pad_screen.dart")
        self.send(p, "press b")
        self.wait_event(log, ["EV_KEY", "BTN_B", 1])
        p.stdin.close()
        p.stdin = None
        self.assertEqual(p.wait(timeout=3), 0)
        self.assertIn(["EV_KEY", "BTN_B", 0], self.events(log))
        self.assertEqual(self.events(log)[-1], ["closed"])

if __name__ == "__main__":
    unittest.main()
