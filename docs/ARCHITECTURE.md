<!-- Updated API contract for startup readiness and asynchronous PDF jobs. -->
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
`app/model_loader.py` loads one model per process during FastAPI lifespan, in a
background thread so readiness polling works while loading. Startup reads only
from the local cache populated by `app.cache_model` during setup. Failed startup
sets error status; fix setup/cache and restart to retry. Model inference is locked;
concurrent runs receive 409. The device route stays available during model work.
A document-level lock also spans upload processing and all PDF pages. PyMuPDF
renders one page at a time at `UNO_PDF_DPI` (150 by default), scaling oversized
pages down to fit the raster budget. The same temporary page image is replaced
each iteration. Page OCR uses the existing single-image model method; there is
no cross-page model context. A single executor runs PDF jobs after upload returns.
A lock protects job snapshots. Per-page results are published as pages finish;
errors preserve earlier pages. The last 20 job records remain in memory, with no
durability across restarts. Temporary files are cleaned on success/error; graceful
shutdown waits for the active job. Force-killing a process can leave temp files.
See [PyMuPDF rendering documentation](https://pymupdf.readthedocs.io/en/latest/recipes-images.html).

Inference uses `eval_mode=True` to obtain text directly, with result-file saving
disabled. Upstream's sliding-window and torch initialization mutations are restored
after inference, including errors. Output is returned verbatim, including model
layout markers, and displayed with `textContent`; no HTML/Markdown execution.

## API

| Request | Response |
| --- | --- |
| `GET /` | Frontend HTML |
| `GET /api/system-info` | `{"device":"cpu","device_name":"CPU","vram_gb":0.0,"model_status":"loading","model_error":null}` |
| `GET /api/upload-config` | `{"max_upload_bytes":0,"pdf_dpi":150}` |
| `POST /api/ocr` | Multipart `file`; images return text/timing; PDFs return `{"job_id":"..."}` after saving |
| `GET /api/ocr/status/{job_id}` | `status`, `pages_done`, `total_pages`, `results`; success adds text/timing, failure adds `error` |

Job status is `processing`, `done`, or `error`. `results` entries contain `page`,
`text`, and `inference_seconds`. Completed jobs also have `page_count`, `pages`,
combined `text` with page separators, and total inference time. Polling every two
seconds gives incremental output. Unknown/expired jobs return 404. The UI stores
its active job ID in sessionStorage to resume polling after refreshing the tab.
Timing excludes model loading/PDF rendering and includes generation and decoding.
Upload errors use HTTP detail: 400 empty file, 413 configured size/pixel limit,
415 invalid image, 422 missing file, 409 document busy, 503 model not ready/storage
failure. PDF validation errors (including encrypted, damaged or empty PDFs) appear
in job status as `error` after acceptance. Existing `/api` URL prefix is retained.
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
