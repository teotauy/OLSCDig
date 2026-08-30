"""Protocol details for Apple Wallet pass updates — these are the bits
that looked internally consistent and still left phones on last week's
match. Run: python3 tests/test_pass_update_protocol.py
"""
import email.utils
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ApnsInvalidTokenTests(unittest.TestCase):
    def test_410_is_invalid(self):
        from wallet_pass import _apns_token_is_invalid
        self.assertTrue(_apns_token_is_invalid(410, ""))

    def test_400_bad_device_token(self):
        from wallet_pass import _apns_token_is_invalid
        self.assertTrue(_apns_token_is_invalid(400, '{"reason":"BadDeviceToken"}'))

    def test_500_is_transient(self):
        from wallet_pass import _apns_token_is_invalid
        self.assertFalse(_apns_token_is_invalid(500, "oops"))


class IfModifiedSinceTests(unittest.TestCase):
    def _check(self, header, last_changed_at):
        # Import the helper without booting the whole Flask app's side effects
        # more than necessary — app.py still loads on import.
        from app import _pass_client_already_has_version
        return _pass_client_already_has_version(header, last_changed_at)

    def test_exact_last_modified_is_current(self):
        last = datetime(2026, 8, 29, 14, 19, 2, tzinfo=timezone.utc)
        header = email.utils.format_datetime(last, usegmt=True)
        self.assertTrue(self._check(header, last))

    def test_now_is_not_treated_as_current_version(self):
        last = datetime(2026, 8, 29, 14, 19, 2, tzinfo=timezone.utc)
        later = datetime(2026, 8, 29, 14, 25, 0, tzinfo=timezone.utc)
        header = email.utils.format_datetime(later, usegmt=True)
        self.assertFalse(self._check(header, last))

    def test_older_timestamp_is_not_current(self):
        last = datetime(2026, 8, 29, 14, 19, 2, tzinfo=timezone.utc)
        older = datetime(2026, 8, 25, 9, 0, 0, tzinfo=timezone.utc)
        header = email.utils.format_datetime(older, usegmt=True)
        self.assertFalse(self._check(header, last))


if __name__ == "__main__":
    unittest.main()
