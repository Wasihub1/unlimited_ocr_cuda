"""Exercise lifespan/readiness using CUDA mocks, never real model construction."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from types import SimpleNamespace
import sys
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import pymupdf
from app.main import app
from app.device import detect_device
from app.model_loader import ModelService


class StartupTests(unittest.TestCase):
    def start(self, cuda, error=None):
        stack = self.enterContext(ExitStack())
        torch = SimpleNamespace(float32='float32', bfloat16='bfloat16', cuda=SimpleNamespace(
            is_available=lambda: cuda,
            get_device_properties=lambda _: SimpleNamespace(name='Mock GPU', total_memory=16 * 1024**3)))
        stack.enter_context(patch.dict(sys.modules, {'torch': torch}))
        detect_device.cache_clear()
        self.addCleanup(detect_device.cache_clear)
        model = ModelService()
        load = stack.enter_context(patch.object(model, '_load', side_effect=error))
        stack.enter_context(patch('app.main.service', model))
        stack.enter_context(patch('app.routes.api.service', model))
        stack.enter_context(patch('app.routes.api.worker', ThreadPoolExecutor(max_workers=1)))
        client = stack.enter_context(TestClient(app))
        for _ in range(200):
            info = client.get('/api/system-info').json()
            if info['model_status'] != 'loading':
                break
            time.sleep(.01)
        return client, model, load, info

    def test_cpu_lifespan_never_touches_model(self):
        client, model, load, info = self.start(False)
        self.assertEqual(info['model_status'], 'unavailable_no_cuda')
        self.assertFalse(info['cuda_available'])
        self.assertFalse(info['ocr_enabled'])
        load.assert_not_called()
        response = client.post('/api/ocr', files={'file': ('test.png', b'data', 'image/png')})
        self.assertEqual(response.status_code, 503)
        self.assertIn('CUDA', response.json()['detail'])
        self.assertEqual(client.get('/').status_code, 200)

    def test_cuda_ready_and_pdf_job(self):
        client, model, load, info = self.start(True)
        self.assertTrue(info['cuda_available'])
        self.assertTrue(info['ocr_enabled'])
        self.assertEqual(info['model_status'], 'ready')
        load.assert_called_once()
        with pymupdf.open() as document:
            document.new_page()
            pdf = document.tobytes()
        with patch.object(model, 'infer', return_value={'text': 'Stub output', 'inference_seconds': .1}):
            response = client.post('/api/ocr', files={'file': ('test.pdf', pdf, 'application/pdf')})
            job_id = response.json()['job_id']
            for _ in range(200):
                result = client.get('/api/ocr/status/' + job_id).json()
                if result['status'] != 'processing':
                    break
                time.sleep(.01)
        self.assertEqual(result['status'], 'done')
        self.assertEqual(result['pages_done'], 1)

    def test_load_error_keeps_server_alive(self):
        client, model, load, info = self.start(True, RuntimeError('simulated load failure'))
        self.assertEqual(info['model_status'], 'error')
        self.assertEqual(info['model_error'], 'simulated load failure')
        self.assertFalse(info['ocr_enabled'])
        self.assertEqual(client.get('/').status_code, 200)
        self.assertEqual(client.post('/api/ocr', files={'file': ('x.png', b'x')}).status_code, 503)
