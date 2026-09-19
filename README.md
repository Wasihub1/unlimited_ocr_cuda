# Unlimited-OCR Test UI

A local FastAPI application with a vanilla HTML/CSS/JavaScript frontend for
Baidu's Unlimited-OCR. Upload a PDF, PNG, JPEG, or WebP and extract text locally.
OCR requires a compatible NVIDIA CUDA GPU; a CPU laptop can run the UI but does
not download or load the model by default.

## Windows quick start

Install Git and put it on PATH, then double-click **run.bat**. Internet is needed
for first-time setup. The launcher finds Python 3.12 or installs it for the current
user, creates `env`, selects CPU/CUDA dependencies, and caches the model on NVIDIA
machines. It starts one server at **http://127.0.0.1:8000** and opens your browser
once `/api/system-info` responds. Use Ctrl+C in the terminal to stop it.

Python detection tries `py -3.12`, `python`, the existing environment, the local
`.tools/python312` runtime, and the default per-user installation directory.
Automatic installation tries winget, then the signed official Python 3.12.10
Windows installer. A wrong-version environment is retained as `env.backup-*` and
replaced with a 3.12 environment. Do not remove `.tools/python312` if your `env`
depends on it. In your IDE select `env/Scripts/python.exe`.

Repeated runs skip pip when the profile and requirements hashes match
`env/.requirements.stamp`. Delete that stamp to repair an incomplete dependency
installation. Model downloads are skipped when a manifest confirms the cached
files still exist with their recorded sizes. Setup failures stop the launcher
before server startup and report the failing step. Logs are in `logs/setup.log`.

```powershell
./run.bat --no-browser
./run.bat --port 8001
./run.bat --force-download --setup-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
.\env\Scripts\python.exe run.py --skip-install --no-browser
```

| Flag | Effect |
| --- | --- |
| `--device auto\|cpu\|cuda` | Select dependency profile (default auto via `nvidia-smi -L`); runtime CUDA availability is always checked by PyTorch |
| `--setup-only` | Complete setup without starting the server |
| `--skip-install` | Reuse dependencies; in setup-only mode still check/cache CUDA weights; during direct server startup reuse the cache |
| `--force-download` | Check/cache weights even without CUDA or with `--skip-install` |
| `--no-browser` | Start without opening a browser |
| `--port 8001` | Change the localhost port (default 8000) |

## CUDA status

The banner and upload controls follow `/api/system-info`:

- **Amber:** CUDA unavailable. No model is loaded and OCR is disabled. The UI and
  information endpoints remain usable.
- **Blue:** CUDA detected; loading the cached model. Uploads wait until ready.
- **Green:** CUDA available and model ready, with GPU name and total VRAM.
- **Red:** model loading failed, with the error, or the server cannot be reached.

The UI polls every three seconds to detect startup progress and server restarts.
OCR requests receive HTTP 503 until ready. An NVIDIA driver compatible with the
PyTorch CUDA 12.9 wheels, bfloat16 support, and enough free VRAM are required.
Real GPU inference and 16 GB compatibility are not validated by the mocked tests.
Python model-loading exceptions become an error state; native driver/library
faults cannot be recovered by a Python exception handler.

## Linux / manual setup

Use Python 3.12 and Git. `run.py` creates `env` and handles dependency installation,
model caching, and startup. It does not install Python on Linux.

```sh
python3.12 run.py --device cuda --setup-only
env/bin/python run.py --skip-install --no-browser
```

Use `--device cpu` on a non-CUDA machine to run the UI with OCR disabled. Keep one
uvicorn worker: additional workers would each allocate their own model.

## Model cache and configuration

Setup downloads the model repository through Hugging Face `snapshot_download`,
without instantiating a model or allocating CPU/GPU model tensors. This avoids
the earlier CPU model-loading crash during setup. A first download is roughly
6-7 GB; setup requires at least 15 GiB free on the cache drive. It makes up to three
attempts, reuses downloaded files, and reports underlying errors. Set `HF_HOME`
(or `HF_HUB_CACHE`) before launching to choose the cache drive. Windows symlink
warnings and Hugging Face telemetry are disabled by the launcher.

At startup, CUDA is checked before importing the model implementation.
`AutoModel`/`AutoTokenizer` load local cached files with `trust_remote_code=True`,
and CUDA uses bfloat16. Upstream custom code executes during model loading;
`UNO_MODEL_REVISION` can pin a reviewed revision (default `main`). The setup
manifest retains that revision until changed or `env/.model-cache.json` is removed.
No weights, environments, vendor downloads, or uploaded documents are committed.

`OCR_MAX_LENGTH` defaults to 16384, range 1024-32768. The legacy `UNO_MAX_LENGTH`
remains an alias; `OCR_MAX_LENGTH` takes precedence. Higher limits increase memory
use and generation time. Output can still be truncated at the configured limit.

## Documents and progress

There is no default byte or PDF page-count cap. `UNO_MAX_UPLOAD_BYTES` optionally
limits upload bytes (`0` disables it). Images have a 25-million-pixel limit.
`UNO_PDF_DPI` controls PDF rendering (default 150, range 36-600); oversized PDF
pages are scaled down to the pixel budget. Disk space, RAM, and runtime still
limit practical document sizes. Encrypted PDFs must be unlocked first.

PDF uploads return a job ID. One in-process worker processes pages sequentially,
publishes progress and per-page text, and preserves partial output if a page fails.
All PDF pages use OCR, including pages containing embedded text. Images use the
synchronous OCR path. One document runs at a time; concurrent submissions get 409.
Temporary files are cleaned after completion or failure.

Jobs are not durable across restarts; the server retains the last 20 job records.
Refreshing the same browser tab resumes polling its job. Output grows to 70vh,
then scrolls internally, and is rendered as text rather than HTML. Timing excludes
model loading and PDF rendering. PDFs show a filename/summary rather than an
embedded PDF viewer.

## Tests and project documentation

```powershell
.\env\Scripts\python.exe -m pip install -r requirements-test.txt
.\env\Scripts\python.exe -m unittest discover -s tests -v
.\env\Scripts\python.exe -m pytest -q
node --check frontend/app.js
node --test tests/frontend.test.cjs
```

- [Architecture and API](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Validation evidence and hardware limitations](docs/VALIDATION.md)
- [Project instructions](AGENTS.md)
- [Original source brief](unocrprompt.md)

After code changes, restart the server and reload the page. Versioned frontend
assets and no-store headers prevent stale UI files. `vendor/unlimited-ocr` is an
ignored reference checkout, retained without pulling; Hugging Face model revision
and vendor revision are independent.
