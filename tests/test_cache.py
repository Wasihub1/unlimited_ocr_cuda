"""Download retries, disk checks and cache reuse without model allocation."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from app import cache_model


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(cache_model, 'ROOT', self.folder))
        self.enterContext(patch('huggingface_hub.constants.HF_HUB_CACHE', str(self.folder)))
        self.free = self.enterContext(patch('app.cache_model.shutil.disk_usage', return_value=SimpleNamespace(free=20 * 1024**3)))
        self.snapshot = self.folder / 'snapshot'
        self.snapshot.mkdir()
        (self.snapshot / 'model.safetensors').write_bytes(b'fake weights')
        (self.snapshot / 'config.json').write_text('{}')

    def test_repeat_skips_download_and_removed_file_invalidates(self):
        with patch('huggingface_hub.snapshot_download', return_value=str(self.snapshot)) as download:
            cache_model.cache_model()
            cache_model.cache_model()
            self.assertEqual(download.call_count, 1)
            (self.snapshot / 'config.json').unlink()
            cache_model.cache_model()
            self.assertEqual(download.call_count, 2)

    def test_low_disk_stops_before_download(self):
        self.free.return_value.free = 1024
        with patch('huggingface_hub.snapshot_download') as download:
            with self.assertRaisesRegex(RuntimeError, '15 GiB'):
                cache_model.cache_model()
            download.assert_not_called()

    def test_network_retry_and_terminal_failure(self):
        with patch('app.cache_model.time.sleep'), patch('huggingface_hub.snapshot_download', side_effect=[ConnectionError('offline'), str(self.snapshot)]) as download:
            cache_model.cache_model()
            self.assertEqual(download.call_count, 2)
        (self.folder / 'env/.model-cache.json').unlink()
        with patch('app.cache_model.time.sleep'), patch('huggingface_hub.snapshot_download', side_effect=ConnectionError('offline')) as download:
            with self.assertRaisesRegex(ConnectionError, 'offline'):
                cache_model.cache_model()
            self.assertEqual(download.call_count, 3)
        self.assertFalse((self.folder / 'env/.model-cache.json').exists())
