<!-- Records execution evidence for the reliability changes in fixes.md. -->
# Validation record

## Reliability and PDF background jobs — 2026-09-17

- Implemented all four changes from `fixes.md` incrementally, including brief
  file comments explaining changes. Setup and run.bat now have separate roles.
- Ran `powershell -NoProfile -ExecutionPolicy Bypass -File setup.ps1`: exit 0.
  CPU dependencies were installed already; the Transformers cache step completed
  and printed `Model cached successfully.` No server was started by setup.
- Ran the real FastAPI lifespan with TestClient and the cached model: observed
  `model_status=loading`, then `ready`, while system-info remained responsive.
  Logged `Model loaded and ready`; shutdown completed successfully. This machine
  has torch 2.10.0+cpu and no available CUDA device. This validates CPU model
  loading, not successful CPU inference or CUDA performance.
- All 17 Python tests passed. Tests use real PDF rendering and mocked inference
  to verify immediate job acceptance, progress before completion, partial output
  after a later-page failure, busy rejection, readiness errors, and cleanup.
- All eight Node DOM-harness tests passed, including readiness gating and job
  polling for success/error with partial output. JS syntax and PowerShell parsing
  passed. Full browser rendering and a 100-page CUDA run remain unverified.
- Transformers emitted an existing checkpoint warning about vision position IDs
  and a torch_dtype deprecation. Neither prevented cache or startup verification.
- PDF jobs are in-process, keep the last 20 records, and do not survive restart.
  Graceful shutdown waits for active work. Output scrolls above 70vh.
- Restarted the confirmed local uvicorn server on port 8000. Live HTTP checks
  returned `model_status=ready`, `device=cpu`, and the updated versioned frontend.

## Initial implementation — 2026-09-17

Environment: Windows PowerShell. Git 2.52.0 and Node 24.11.1 are available.
`python`, `py`, and `uv` were not found on PATH. No `nvidia-smi` was found.

- Original brief and official upstream inference/model code reviewed.
- API tests cover frontend serving, device JSON, empty/corrupt/missing images,
  byte limit, successful response, temporary-file cleanup, busy and model errors.
- Python tests, dependency installation, server boot, and real model inference
  have not run: a Python runtime is unavailable in this environment.
- `node --check frontend/app.js`: passed (exit 0).
- Vendor clone: completed successfully at
  `d49ff64afffc1f47ab563dc1c589bc2f78808fa4`. The sandbox's first network attempt
  failed with a Windows credential error; the approved retry succeeded. The
  sandbox user cannot run Git inspection against the user-owned clone without a
  safe-directory exception; revision was read directly from `.git/refs/heads/main`.
- Interactive browser, CPU loading, CUDA inference, output quality, and 16 GB
  memory usage remain unverified.

## Acceptance procedure

1. Install Python 3.12 and run the README setup for the chosen profile.
2. Install test dependencies and run `python -m unittest discover -s tests -v`.
3. Start the server. Verify `/`, assets, `/api/system-info`, and `/docs` work
   before any weight download. Check the actual CPU/CUDA badge.
4. Upload a small known text image by browse and drag/drop. Check preview, busy
   state, extracted text, timing, and readable failures. Try corrupt and large files.
5. On CPU, attempt the first request and record whether loading succeeds and the
   exact CUDA compatibility failure if inference fails. Verify the app still responds.
6. On a 16 GB CUDA machine, record GPU/driver/PyTorch/model revision, load time,
   peak VRAM, text accuracy, and inference time for a short image and a dense page.
7. Repeat after the first successful load; verify no second model load in logs.
   Submit two concurrent requests; one should return 409 during model execution.
8. Confirm temporary directories disappear after successful and failed requests.

Append observed evidence; keep pending checks explicit until performed.

## PDF and flexible upload scope — 2026-09-17

- `env\Scripts\python.exe -m unittest discover -s tests -v`: all 12 tests passed.
  PDF rendering uses real PyMuPDF and generated two-page documents; OCR is mocked.
- Verified ordered page results and timing totals, a PDF over 11 MiB with the
  byte cap disabled, configured limit enforcement, corrupt/password-protected PDF
  errors, concurrent-document rejection, cleanup after model failures, and retry.
- Fixed a Windows temporary-file lock when PyMuPDF rejected malformed PDF input
  opened through its filetype override; open the saved `.pdf` path directly.
- `node --check frontend/app.js`: passed. Interactive browser checks remain pending.
- Updated AGENTS.md, README, architecture, and roadmap to include PDF uploads and
  `UNO_MAX_UPLOAD_BYTES=0` (no fixed default byte cap). Upload data is copied in
  chunks and PDF pages are rasterized one at a time.
- Real PDF/model inference remains pending. Test at least one scanned multipage
  PDF and one PDF with embedded text on the target CUDA machine, recording page
  accuracy, total duration, RAM/VRAM, and temporary disk usage.

## Stale PDF upload UI correction — 2026-09-17

- Live port 8000 returned current PDF-aware JavaScript but no cache-control header;
  `/api/upload-config` returned 404, confirming an older backend was still running.
  The reported image-only validation string no longer exists in current sources.
- Added versioned frontend asset URLs and no-store response headers for HTML/assets.
- All 13 Python API tests passed, including HTML/script cache behavior.
- All four Node DOM-harness tests passed: PDF selection with standard, missing,
  and generic MIME types enables OCR and shows selection; PDF drop recovers after
  invalid-file validation. These execute the actual JS against IDs from the HTML,
  but are not full browser tests. JavaScript syntax checking passed.
- Identified and restarted the old project uvicorn process on port 8000. Live
  checks now return 200 for `/`, the versioned script, and `/api/upload-config`;
  HTML/script responses have `Cache-Control: no-store`. Configuration reports
  `max_upload_bytes: 0` and `pdf_dpi: 150`. Server logs are in ignored
  `.tools/server.stdout.log` and `.tools/server.stderr.log`.

## Local Python environment — 2026-09-17

- Installed Python 3.12.10 using the existing Python install manager:
  `py install --target="D:\unlimited ocr\.tools\python312" 3.12`.
  Download needed an approved retry outside the sandbox. The manager also
  reported updating itself to 26.3; no system Python runtime replacement was requested.
- Created `env` with `.tools\python312\python.exe -m venv env`.
  Verified `env\Scripts\python.exe` reports Python 3.12.10, pip 25.0.1,
  and `sys.prefix != sys.base_prefix`. Base runtime is `.tools/python312`.
- Changed the launcher and setup documentation to use `env`; ignored it in Git.
- Installed `requirements-test.txt` in `env`. All six API tests passed with
  `env\Scripts\python.exe -m unittest discover -s tests -v`.
  Device/model calls are mocked; this does not establish real OCR compatibility.
- `env\Scripts\python.exe run.py --help` passed.
- Full CPU/CUDA dependencies, live server boot, and real model inference remain
  pending. The earlier missing-Python blocker is resolved.
