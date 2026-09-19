"""Configuration bounds and browser readiness are checked without opening a browser."""
import importlib
import os
import threading
import unittest
from unittest.mock import MagicMock, patch
from app import config
import run


class ConfigurationTests(unittest.TestCase):
    def test_length_default_alias_precedence_and_bounds(self):
        original = dict(os.environ)
        try:
            for key in ['OCR_MAX_LENGTH', 'UNO_MAX_LENGTH']:
                os.environ.pop(key, None)
            self.assertEqual(importlib.reload(config).MAX_LENGTH, 16384)
            os.environ['UNO_MAX_LENGTH'] = '4096'
            self.assertEqual(importlib.reload(config).MAX_LENGTH, 4096)
            os.environ['OCR_MAX_LENGTH'] = '8192'
            self.assertEqual(importlib.reload(config).MAX_LENGTH, 8192)
            for value in ['0', '32769']:
                os.environ['OCR_MAX_LENGTH'] = value
                with self.assertRaises(ValueError):
                    importlib.reload(config)
        finally:
            os.environ.clear()
            os.environ.update(original)
            importlib.reload(config)

    def test_browser_waits_for_successful_response(self):
        response = MagicMock()
        response.__enter__.return_value.status = 200
        with patch('run.urllib.request.urlopen', side_effect=[OSError('not listening'), response]) as request, patch('run.webbrowser.open') as browser:
            run.open_when_ready('http://127.0.0.1:8000', threading.Event())
            self.assertEqual(request.call_count, 2)
            browser.assert_called_once_with('http://127.0.0.1:8000')

    def test_browser_cancels_when_server_stops(self):
        stop = threading.Event()
        stop.set()
        with patch('run.webbrowser.open') as browser, patch('run.urllib.request.urlopen') as request:
            run.open_when_ready('http://127.0.0.1:8000', stop)
            browser.assert_not_called()
            request.assert_not_called()
