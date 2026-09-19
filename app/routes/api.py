"""Gate OCR on CUDA readiness; retain sequential PDF jobs with partial results."""
import math
import copy
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import tempfile
import threading
import warnings
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
import pymupdf
from starlette.concurrency import run_in_threadpool

from app.config import MAX_IMAGE_PIXELS, MAX_UPLOAD_BYTES, PDF_DPI
from app.device import detect_device
from app.model_loader import ModelBusy, ModelError, service

router = APIRouter(prefix="/api")
document_lock = threading.Lock()
jobs_lock = threading.Lock()
jobs = OrderedDict()
worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pdf-ocr")


def wait_for_jobs():
    worker.shutdown(wait=True)


def update_job(job_id, **changes):
    with jobs_lock:
        jobs[job_id].update(changes)


@router.get("/ocr/status/{job_id}")
def job_status(job_id: str):
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(404, "Job not found or expired. Jobs are lost on server restart.")
        return copy.deepcopy(jobs[job_id])


def run_pdf_job(job_id, source, folder, temporary):
    final = {}
    try:
        def progress(pages, total):
            update_job(job_id, pages_done=len(pages), total_pages=total, results=list(pages))
        result = process_pdf(source, folder, progress)
        final = {"status": "done", **result}
    except Exception as exc:
        final = {"status": "error", "error": str(getattr(exc, "detail", exc))}
    finally:
        try:
            temporary.cleanup()
        except OSError as exc:
            final = {"status": "error", "error": f"Temporary file cleanup failed: {exc}"}
        finally:
            document_lock.release()
            update_job(job_id, **final)


@router.get("/system-info")
def system_info():
    hardware = detect_device()
    cuda = hardware.device == "cuda"
    enabled = cuda and service.status == "ready"
    message = (
        "CUDA is not available on this device - OCR is disabled" if not cuda else
        "CUDA is available - you can OCR now" if enabled else
        service.error or "Model is loading, please wait..."
    )
    return {"device": hardware.device, "device_name": hardware.device_name,
            "vram_gb": hardware.vram_gb, "cuda_available": cuda,
            "gpu_name": hardware.device_name if cuda else None,
            "vram_total_gb": hardware.vram_gb, "model_status": service.status,
            "model_error": service.error, "ocr_enabled": enabled, "message": message}


@router.get("/upload-config")
def upload_config():
    return {"max_upload_bytes": MAX_UPLOAD_BYTES, "pdf_dpi": PDF_DPI}


def process_image(source, folder):
    image_path = folder / "input.png"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source) as image:
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise HTTPException(413, "Image exceeds 25 million pixels.")
                if image.format not in {"PNG", "JPEG", "WEBP"}:
                    raise HTTPException(415, "Use a PDF, PNG, JPEG, or WebP file.")
                ImageOps.exif_transpose(image).convert("RGB").save(image_path)
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise HTTPException(413, "Image dimensions are too large.") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(415, "The file is not a readable PDF, PNG, JPEG, or WebP.") from exc
    return service.infer(image_path, folder / "result")


def process_pdf(source, folder, progress=None):
    pdf_path = folder / "input.pdf"
    source.rename(pdf_path)
    try:
        # Open by .pdf path: filetype override opens an extra stream which can
        # remain locked on Windows when PyMuPDF rejects a malformed document.
        document = pymupdf.open(pdf_path)
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise HTTPException(415, "The PDF could not be opened. It may be damaged.") from exc
    pages = []
    with document:
        if not document.is_pdf:
            raise HTTPException(415, "The file is not a PDF document.")
        if document.needs_pass:
            raise HTTPException(400, "This PDF is password protected. Upload an unlocked copy.")
        if not document.page_count:
            raise HTTPException(400, "The PDF contains no pages.")
        if progress:
            progress([], document.page_count)
        for number in range(document.page_count):
            image_path = folder / "page.png"
            try:
                page = document.load_page(number)
                scale = PDF_DPI / 72
                width, height = page.rect.width, page.rect.height
                if width <= 0 or height <= 0 or not math.isfinite(width * height):
                    raise ValueError("Invalid page dimensions")
                # Bound each raster without limiting document bytes or page count.
                while math.ceil(width * scale) * math.ceil(height * scale) > MAX_IMAGE_PIXELS:
                    scale *= 0.8
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csRGB, alpha=False)
                pixmap.save(image_path)
                del pixmap
            except (RuntimeError, ValueError) as exc:
                raise HTTPException(415, f"Could not render PDF page {number + 1}: {exc}") from exc
            try:
                result = service.infer(image_path, folder / "result")
            except ModelBusy:
                raise
            except ModelError as exc:
                raise ModelError(f"PDF page {number + 1}: {exc}") from exc
            finally:
                image_path.unlink(missing_ok=True)
            pages.append({"page": number + 1, **result})
            if progress:
                progress(pages, document.page_count)
    return {
        "text": "\n\n".join(f"--- Page {p['page']} ---\n{p['text']}" for p in pages),
        "inference_seconds": round(sum(p["inference_seconds"] for p in pages), 3),
        "page_count": len(pages), "pages": pages,
    }


def process_upload(upload):
    info = system_info()
    if not info["ocr_enabled"]:
        raise HTTPException(503, info["message"])
    if not document_lock.acquire(blocking=False):
        raise HTTPException(409, "Another document is being processed. Try again after it finishes.")
    handed_off = False
    temporary = None
    try:
        temporary = tempfile.TemporaryDirectory(prefix="unlimited-ocr-")
        folder = Path(temporary.name)
        source = folder / "upload"
        size = 0
        signature = b""
        with source.open("wb") as destination:
            while chunk := upload.file.read(1024 * 1024):
                if not signature:
                    signature = chunk[:1024]
                size += len(chunk)
                if MAX_UPLOAD_BYTES and size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, f"File exceeds the configured {MAX_UPLOAD_BYTES} byte upload limit.")
                destination.write(chunk)
        if not size:
            raise HTTPException(400, "Choose a non-empty file.")
        is_pdf = b"%PDF-" in signature or (upload.filename or "").lower().endswith(".pdf")
        if is_pdf:
            job_id = uuid.uuid4().hex
            with jobs_lock:
                # One active document; retain only the last 20 job results.
                while len(jobs) >= 20:
                    jobs.popitem(last=False)
                jobs[job_id] = {"status": "processing", "pages_done": 0, "total_pages": 0, "results": []}
            worker.submit(run_pdf_job, job_id, source, folder, temporary)
            handed_off = True
            return {"job_id": job_id}
        # A single image is short enough for the existing synchronous path.
        return process_image(source, folder)
    except ModelBusy as exc:
        raise HTTPException(409, str(exc)) from exc
    except ModelError as exc:
        raise HTTPException(503, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(503, "Could not store or process the file. Check available temporary disk space.") from exc
    finally:
        if not handed_off:
            try:
                if temporary:
                    temporary.cleanup()
            finally:
                document_lock.release()


@router.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    try:
        return await run_in_threadpool(process_upload, file)
    finally:
        await file.close()
