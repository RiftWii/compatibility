import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from build_list import aggregate, parse_issue_body, version_key


SAMPLE_BODY = """### Game ID

RMGE01

### Game name

Mario Kart Wii

### Game type

Wii

### How it runs

Playable

### Loaded from

USB drive

### File type

WBFS

### Console

Wii

### cIOS

_No response_

### Controller

Wii Remote, Classic Controller

### USB pad model

_No response_

### Mods

_No response_

### RiftWii version

2611-42

### Notes

Works well.

### Problem report link

_No response_
"""


class TestParse(unittest.TestCase):
    def test_sample_body(self):
        d = parse_issue_body(SAMPLE_BODY)
        self.assertEqual(d["game_id"], "RMGE01")
        self.assertEqual(d["game_name"], "Mario Kart Wii")
        self.assertEqual(d["platform"], "Wii")
        self.assertEqual(d["status"], "Playable")
        self.assertEqual(d["console"], "Wii")
        self.assertEqual(d["version"], "2611-42")
        self.assertEqual(d["controller"], "Wii Remote, Classic Controller")
        self.assertEqual(d["cios"], "")
        self.assertEqual(d["usb_pad"], "")
        self.assertEqual(d["mods"], "")
        self.assertEqual(d["problem_report"], "")


class TestVersionKey(unittest.TestCase):
    def test_ordering(self):
        self.assertLess(version_key("2610-810"), version_key("2611-3"))
        self.assertLess(version_key("2611-3"), version_key("2611-42"))

    def test_garbage_lowest(self):
        self.assertLess(version_key("garbage"), version_key("2610-1"))
        self.assertLess(version_key(""), version_key("2610-1"))
        self.assertEqual(version_key("oops"), (-1, -1))


def _report(game_id="RMGE01", name="Mario Kart Wii", platform="Wii", status="Perfect", version="2611-42", console="Wii", url="https://example.com/1"):
    return {
        "game_id": game_id,
        "game_name": name,
        "platform": platform,
        "status": status,
        "version": version,
        "console": console,
        "url": url,
    }


class TestAggregate(unittest.TestCase):
    def test_newest_version_wins(self):
        reports = [
            _report(status="Perfect", version="2610-1", url="https://example.com/old"),
            _report(status="Has problems", version="2611-42", url="https://example.com/new"),
        ]
        games = aggregate(reports)
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["status"], "Has problems")

    def test_tie_goes_to_worse(self):
        reports = [
            _report(status="Perfect", version="2611-42", url="https://example.com/a"),
            _report(status="Playable", version="2611-42", url="https://example.com/b"),
        ]
        games = aggregate(reports)
        self.assertEqual(games[0]["status"], "Playable")
        reports2 = [
            _report(status="Perfect", version="2611-42", url="https://example.com/a"),
            _report(status="Won't start", version="2611-42", url="https://example.com/b"),
        ]
        games2 = aggregate(reports2)
        self.assertEqual(games2[0]["status"], "Won't start")

    def test_dolphin_only_marked(self):
        reports = [
            _report(status="Playable", version="2611-42", console="Dolphin (emulator)", url="https://example.com/d"),
        ]
        games = aggregate(reports)
        self.assertEqual(len(games), 1)
        self.assertTrue(games[0]["dolphin_only"])
        self.assertEqual(games[0]["status"], "Playable")
        self.assertEqual(games[0]["console_count"], 0)
        self.assertEqual(games[0]["dolphin_count"], 1)

    def test_dolphin_does_not_change_console_status(self):
        reports = [
            _report(status="Perfect", version="2611-42", console="Wii", url="https://example.com/c"),
            _report(status="Won't start", version="2611-42", console="Dolphin (emulator)", url="https://example.com/d"),
        ]
        games = aggregate(reports)
        self.assertEqual(len(games), 1)
        self.assertFalse(games[0]["dolphin_only"])
        self.assertEqual(games[0]["status"], "Perfect")
        self.assertEqual(games[0]["console_status"], "Perfect")
        self.assertEqual(games[0]["dolphin_status"], "Won't start")


class NotesHeadingTest(unittest.TestCase):
    def test_heading_in_notes_stays_in_notes(self):
        body = SAMPLE_BODY.replace("### Notes\n\n", "### Notes\n\n### How it runs\n\nWon't start\n\n", 1)
        self.assertIn("### How it runs", body)
        parsed = parse_issue_body(body)
        self.assertNotEqual(parsed["status"], "Won't start")
        self.assertIn("Won't start", parsed["notes"])


if __name__ == "__main__":
    unittest.main()
