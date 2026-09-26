"""Regression tests for AI Days alerts and persisted link history."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import ai_days_monitor
import monitor


class AIListingAlertsTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.state_file = patch.object(monitor, "STATE_FILE", Path(self.folder.name) / "monitor_state.json")
        self.state_file.start()
        self.addCleanup(self.state_file.stop)
        self.secrets = patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "dummy", "TELEGRAM_CHAT_ID": "dummy"})
        self.secrets.start()
        self.addCleanup(self.secrets.stop)
        self.playwright = MagicMock()
        self.playwright.__enter__.return_value = MagicMock()
        self.imported_playwright = patch.dict("sys.modules", {"playwright": MagicMock(),
                                                           "playwright.sync_api": MagicMock(sync_playwright=lambda: self.playwright)})
        self.imported_playwright.start()
        self.addCleanup(self.imported_playwright.stop)

    @patch.object(ai_days_monitor, "send_telegram_text")
    @patch.object(ai_days_monitor, "find_registration_links")
    def test_existing_links_are_ignored_and_new_link_is_sent_once(self, find_links, send):
        find_links.return_value = [
            ("מחזור ראשון", "ישן", "https://www.eventer.co.il/t242f/?utm_source=technion"),
            ("מחזור שלישי", "פיתוח & למידה", "https://www.eventer.co.il/new3?utm_source=technion"),
            ("מחזור שלישי", "פיתוח & למידה", "https://eventer.co.il/new3/"),
        ]
        ai_days_monitor.main()
        ai_days_monitor.main()
        send.assert_called_once()
        message = send.call_args.args[0]
        self.assertIn("🟠<b>עדכון חשוב!</b>", message)
        self.assertIn("<b>מחזור שלישי</b>", message)
        self.assertIn("פיתוח &amp; למידה", message)
        self.assertEqual(send.call_args.kwargs["parse_mode"], "HTML")
        self.assertEqual(monitor.load_state()["_ai_days_seen_links"], ["https://eventer.co.il/new3"])

    @patch.object(ai_days_monitor, "send_telegram_text", side_effect=RuntimeError("Telegram failed"))
    @patch.object(ai_days_monitor, "find_registration_links", return_value=[
        ("מחזור שלישי", "חדש", "https://www.eventer.co.il/new3")
    ])
    def test_failed_send_does_not_mark_link_as_seen(self, find_links, send):
        with self.assertRaisesRegex(RuntimeError, "Telegram failed"):
            ai_days_monitor.main()
        self.assertFalse(monitor.STATE_FILE.exists())


if __name__ == "__main__":
    unittest.main()
