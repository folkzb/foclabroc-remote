"""Exercise the embedded uinput protocol without root or Batocera hardware."""
import base64
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

    def start(self, path, player=1):
        source = (ROOT / path).read_text()
        script = re.search(r"const _padScript = r'''(.*?)''';", source, re.S).group(1)
        compile(script, path, "exec")
        log = self.base / ("events" + str(len(self.processes)) + ".jsonl")
        env = dict(os.environ, VPAD_TEST_LOG=str(log), PYTHONPATH=str(self.base),
                   VPAD_LOCK_DIR=str(self.base / "locks"))
        payload = base64.b64encode(script.encode()).decode()
        process = subprocess.Popen([sys.executable, "-u", "-c",
            f"import base64; exec(base64.b64decode(\'{payload}\'))"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        self.processes.append(process)
        self.assertTrue(select.select([process.stdout], [], [], 3)[0], "Missing READY")
        expected = f"READY:{player}\n".encode() if player is not None else b"ERR:players_busy\n"
        self.assertEqual(process.stdout.readline(), expected)
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


    def test_two_players_have_independent_devices_and_inputs(self):
        first, first_log = self.start("lib/screens/virtual_pad_screen.dart", player=1)
        second, second_log = self.start("batocera_remote_en/lib/screens/virtual_pad_screen.dart", player=2)
        self.assertEqual(self.events(first_log)[0][2]["name"], "Foclabroc-VPad P1")
        self.assertEqual(self.events(second_log)[0][2]["name"], "Foclabroc-VPad P2")
        self.assertNotEqual(self.events(first_log)[0][2]["phys"], self.events(second_log)[0][2]["phys"])
        self.send(first, "press a\nstick left 15000 -5000")
        self.send(second, "press b\nstick right -9000 18000")
        self.wait_event(first_log, ["EV_ABS", "ABS_Y", -5000])
        self.wait_event(second_log, ["EV_ABS", "ABS_RY", 18000])
        self.assertNotIn(["EV_KEY", "BTN_B", 1], self.events(first_log))
        self.assertNotIn(["EV_KEY", "BTN_A", 1], self.events(second_log))
        before = self.events(second_log)
        self.send(first, "quit")
        self.assertEqual(first.wait(timeout=3), 0)
        self.assertEqual(self.events(second_log), before, "Stopping P1 affected P2")
        replacement, replacement_log = self.start("lib/screens/virtual_pad_screen.dart", player=1)
        self.assertEqual(self.events(replacement_log)[0][2]["phys"], self.events(first_log)[0][2]["phys"])
        self.assertIsNone(second.poll())
        self.send(second, "release b")
        self.wait_event(second_log, ["EV_KEY", "BTN_B", 0])

    def test_slots_are_exclusive_and_release_after_process_crash(self):
        controllers = [self.start("lib/screens/virtual_pad_screen.dart", player=i) for i in range(1, 5)]
        rejected, _ = self.start("lib/screens/virtual_pad_screen.dart", player=None)
        self.assertEqual(rejected.wait(timeout=3), 1)
        controllers[1][0].kill()
        controllers[1][0].wait(timeout=3)
        replacement, log = self.start("lib/screens/virtual_pad_screen.dart", player=2)
        self.assertEqual(self.events(log)[0][2]["name"], "Foclabroc-VPad P2")
        for index in (0, 2, 3):
            self.assertIsNone(controllers[index][0].poll())

    def test_abandoned_connection_frees_its_slot_without_affecting_active_player(self):
        abandoned, abandoned_log = self.start("lib/screens/virtual_pad_screen.dart", player=1)
        active, active_log = self.start("lib/screens/virtual_pad_screen.dart", player=2)
        self.send(active, "press a")
        self.wait_event(active_log, ["EV_KEY", "BTN_A", 1])
        deadline = time.monotonic() + 12
        while abandoned.poll() is None and time.monotonic() < deadline:
            self.send(active, "ping")
            time.sleep(0.3)
        self.assertEqual(abandoned.poll(), 0)
        self.assertEqual(self.events(abandoned_log)[-1], ["closed"])
        self.assertIsNone(active.poll())
        self.assertNotIn(["EV_KEY", "BTN_A", 0], self.events(active_log))
        replacement, _ = self.start("lib/screens/virtual_pad_screen.dart", player=1)
        self.assertIsNone(replacement.poll())

if __name__ == "__main__":
    unittest.main()
