# Architecture and API

`app/main.py` serves `frontend/` and registers `app/routes/api.py`. Routes validate
uploads and run blocking image/model work in a thread pool. Requests use unique
temporary directories that are removed on success or failure. Filenames supplied
by clients are never used as paths. PDF/PNG/JPEG/WebP are accepted, with no default
byte cap. `UNO_MAX_UPLOAD_BYTES` optionally sets one (0 disables it). Uploads are
copied from the multipart spool to disk in 1 MiB chunks, not read fully into RAM.
Image rasters retain a 25-million-pixel limit. The optional byte limit is checked after multipart parsing: this
localhost prototype is not a public ingress server with a streaming body limit.

`app/device.py` caches CUDA detection and resolves CUDA/bfloat16 or CPU/float32.
`app/model_loader.py` owns one lazy model per process. A nonblocking lock covers
loading and inference; concurrent runs receive 409. The device route stays
available during model work. Failed loads leave the singleton unset for retry.
A document-level lock also spans upload processing and all PDF pages. PyMuPDF
renders one page at a time at `UNO_PDF_DPI` (150 by default), scaling oversized
pages down to fit the raster budget. The same temporary page image is replaced
each iteration. Page OCR uses the existing single-image model method; there is
no cross-page model context. Text results accumulate in memory until response.
See [PyMuPDF rendering documentation](https://pymupdf.readthedocs.io/en/latest/recipes-images.html).

Inference uses `eval_mode=True` to obtain text directly, with result-file saving
disabled. Upstream's sliding-window and torch initialization mutations are restored
after inference, including errors. Output is returned verbatim, including model
layout markers, and displayed with `textContent`; no HTML/Markdown execution.

## API

| Request | Response |
| --- | --- |
| `GET /` | Frontend HTML |
| `GET /api/system-info` | `{"device":"cpu","device_name":"CPU","vram_gb":0.0}` |
| `GET /api/upload-config` | `{"max_upload_bytes":0,"pdf_dpi":150}` |
| `POST /api/ocr` | Multipart field `file`; `{"text":"…","inference_seconds":1.23}` |

PDF responses additionally contain `page_count` and `pages` (each with `page`,
`text`, and `inference_seconds`). Combined `text` has page separators; total timing
is the sum of page inference times. No partial success is returned for a failed PDF.
Timing excludes model loading/PDF rendering and includes generation and decoding. HTTP errors
use `{"detail":"readable message"}`: 400 empty file, 413 oversized bytes/pixels,
415 unsupported/corrupt document, 422 missing field, 409 busy document/model,
503 model/storage failure. Password-protected or zero-page PDFs receive 400.
FastAPI exposes interactive API documentation at `/docs`.

## Upstream decisions

Checked 2026-09-17 against the [official repository](https://github.com/baidu/unlimited-ocr)
and [model implementation](https://huggingface.co/baidu/Unlimited-OCR/blob/main/modeling_unlimitedocr.py).
Dependencies follow the upstream Transformers recipe; CPU/CUDA torch wheels are
selected separately. CUDA is the documented inference path. Direct CUDA calls in
custom code prevent promising CPU inference. The supplied prompt's expectation
that CPU model loading always succeeds is therefore an acceptance experiment.

The vendor clone is reference material, not an import dependency. Model revision
and vendor revision are independent. Default `main` can change; set
`UNO_MODEL_REVISION` to a reviewed model commit when reproducing results.
