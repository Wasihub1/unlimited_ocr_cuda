"""Regression coverage for startup readiness and asynchronous PDF progress."""
import time
import threading
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
import pymupdf

from app.main import app
from app.device import Hardware
from app.model_loader import ModelBusy, ModelError


class ApiTests(unittest.TestCase):
    def setUp(self):
        ready = patch("app.routes.api.service.status", "ready")
        ready.start()
        self.addCleanup(ready.stop)
        hardware = patch("app.routes.api.detect_device", return_value=Hardware("cuda", "Fake GPU", 16, None))
        hardware.start()
        self.addCleanup(hardware.stop)
        self.client = TestClient(app)
        data = io.BytesIO()
        Image.new("RGB", (8, 8), "white").save(data, format="PNG")
        self.image = data.getvalue()

    def upload(self, data=None):
        return self.client.post("/api/ocr", files={"file": ("../../image.png", self.image if data is None else data, "image/png")})

    def test_frontend_and_assets(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/static/app.js").status_code, 200)
        self.assertEqual(self.client.get("/static/../app/config.py").status_code, 404)

    def test_frontend_cache_and_pdf_script(self):
        import re
        page = self.client.get("/")
        self.assertEqual(page.headers["cache-control"], "no-store")
        script_path = re.search(r'<script src="([^"]+)"', page.text).group(1)
        self.assertIn("?v=", script_path)
        script = self.client.get(script_path)
        self.assertEqual(script.status_code, 200)
        self.assertEqual(script.headers["cache-control"], "no-store")
        self.assertIn("Choose a PDF, PNG, JPEG, or WebP file.", script.text)

    @patch("app.routes.api.detect_device", return_value=Hardware("cpu", "CPU", 0, None))
    def test_device(self, _):
        info = self.client.get("/api/system-info").json()
        self.assertFalse(info["cuda_available"])
        self.assertFalse(info["ocr_enabled"])
        self.assertEqual(info["device"], "cpu")

    def test_invalid_and_empty_images(self):
        self.assertEqual(self.upload(b"not an image").status_code, 415)
        self.assertEqual(self.upload(b"").status_code, 400)
        self.assertEqual(self.client.post("/api/ocr").status_code, 422)

    @patch("app.routes.api.MAX_UPLOAD_BYTES", 4)
    def test_size_limit(self):
        self.assertEqual(self.upload().status_code, 413)

    def test_result_and_cleanup(self):
        paths = []

        def infer(image, output):
            paths.append(Path(image))
            self.assertTrue(Path(image).is_file())
            self.assertEqual(Path(image).name, "input.png")
            return {"text": "Example text", "inference_seconds": 0.1}

        with patch("app.routes.api.service.infer", side_effect=infer):
            response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["text"], "Example text")
        self.assertFalse(paths[0].parent.exists())

    def test_model_errors_remain_readable(self):
        for error, status in [(ModelBusy("Busy"), 409), (ModelError("CUDA required"), 503)]:
            with patch("app.routes.api.service.infer", side_effect=error):
                response = self.upload()
            self.assertEqual(response.status_code, status)
            self.assertEqual(response.json()["detail"], str(error))

    def pdf_bytes(self, encrypted=False):
        with pymupdf.open() as document:
            for text in ["First page", "Second page"]:
                document.new_page(width=200, height=200).insert_text((20, 30), text)
            if encrypted:
                return document.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="secret")
            return document.tobytes()

    def upload_pdf(self, data):
        response = self.client.post("/api/ocr", files={"file": ("document.pdf", data, "application/pdf")})
        if "job_id" not in response.json():
            return response
        return self.wait_job(response.json()["job_id"])

    def wait_job(self, job_id):
        for _ in range(300):
            response = self.client.get(f"/api/ocr/status/{job_id}")
            if response.json()["status"] != "processing":
                return response
            time.sleep(0.01)
        self.fail("Job failed to finish")

    def test_pdf_pages_and_cleanup(self):
        paths = []
        def infer(image, output):
            paths.append(Path(image))
            with Image.open(image) as rendered:
                self.assertEqual(rendered.mode, "RGB")
            return {"text": f"Text {len(paths)}", "inference_seconds": 0.2}
        with patch("app.routes.api.service.infer", side_effect=infer):
            response = self.upload_pdf(self.pdf_bytes())
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["page_count"], 2)
        self.assertEqual([p["text"] for p in result["pages"]], ["Text 1", "Text 2"])
        self.assertEqual(result["inference_seconds"], 0.4)
        self.assertIn("--- Page 2 ---", result["text"])
        self.assertTrue(all(not p.parent.exists() for p in paths))

    def test_invalid_and_encrypted_pdf(self):
        self.assertEqual(self.upload_pdf(b"%PDF-broken").json()["status"], "error")
        self.assertIn("password protected", self.upload_pdf(self.pdf_bytes(encrypted=True)).json()["error"])

    @patch("app.routes.api.MAX_UPLOAD_BYTES", 0)
    def test_file_larger_than_ten_mib(self):
        data = self.pdf_bytes() + b"\n%" + b" " * (11 * 1024 * 1024)
        with patch("app.routes.api.service.infer", return_value={"text": "Text", "inference_seconds": 0.1}):
            self.assertEqual(self.upload_pdf(data).status_code, 200)

    def test_pdf_failure_cleanup_and_retry(self):
        paths = []
        def fail(image, output):
            paths.append(Path(image))
            raise ModelError("Failure")
        with patch("app.routes.api.service.infer", side_effect=fail):
            response = self.upload_pdf(self.pdf_bytes())
        self.assertEqual(response.json()["status"], "error")
        self.assertIn("PDF page 1", response.json()["error"])
        self.assertFalse(paths[0].parent.exists())
        with patch("app.routes.api.service.infer", return_value={"text": "Recovered", "inference_seconds": 0.1}):
            self.assertEqual(self.upload_pdf(self.pdf_bytes()).status_code, 200)

    def test_document_busy(self):
        from app.routes.api import document_lock
        with document_lock:
            self.assertEqual(self.upload_pdf(self.pdf_bytes()).status_code, 409)

    @patch("app.routes.api.MAX_UPLOAD_BYTES", 12345)
    def test_upload_configuration(self):
        self.assertEqual(self.client.get("/api/upload-config").json()["max_upload_bytes"], 12345)


    def test_readiness_blocks_uploads(self):
        with patch("app.routes.api.service.status", "loading"):
            self.assertEqual(self.upload().status_code, 503)

    def test_unknown_job(self):
        self.assertEqual(self.client.get("/api/ocr/status/missing").status_code, 404)

    def test_partial_progress_before_completion_and_failure(self):
        entered_second = threading.Event()
        release = threading.Event()
        calls = []
        def infer(image, output):
            calls.append(1)
            if len(calls) == 2:
                entered_second.set()
                release.wait(3)
                raise ModelError("Second page failed")
            return {"text": "First page text", "inference_seconds": 0.2}
        with patch("app.routes.api.service.infer", side_effect=infer):
            response = self.client.post("/api/ocr", files={"file": ("test.pdf", self.pdf_bytes(), "application/pdf")})
            job_id = response.json()["job_id"]
            try:
                self.assertTrue(entered_second.wait(2))
                progress = self.client.get(f"/api/ocr/status/{job_id}").json()
                self.assertEqual(progress["status"], "processing")
                self.assertEqual(progress["pages_done"], 1)
                self.assertEqual(progress["total_pages"], 2)
                self.assertEqual(progress["results"][0]["text"], "First page text")
                self.assertEqual(self.upload().status_code, 409)
            finally:
                release.set()
                final = self.wait_job(job_id).json()
            self.assertEqual(final["status"], "error")
            self.assertEqual(len(final["results"]), 1)

    @patch("app.model_loader.detect_device", return_value=Hardware("cuda", "Fake GPU", 16, None))
    def test_model_initialize_once_and_error(self, _):
        from app.model_loader import ModelService
        model = ModelService()
        with patch.object(model, "_load") as load:
            model.initialize()
            model.initialize()
            self.assertEqual(model.status, "ready")
            load.assert_called_once()
        failed = ModelService()
        with patch.object(failed, "_load", side_effect=RuntimeError("cache missing")):
            failed.initialize()
        self.assertEqual(failed.status, "error")
        self.assertEqual(failed.error, "cache missing")


if __name__ == "__main__":
    unittest.main()
