# Unlimited-OCR Test UI

A local FastAPI application with a plain HTML/CSS/JavaScript frontend. Upload a
PDF, PNG, JPEG, or WebP file and run Baidu's Unlimited-OCR. Images show a preview;
PDFs show a selection summary and are processed page by page in order.

There is no fixed upload byte limit by default. To set one, define
`UNO_MAX_UPLOAD_BYTES` before starting (`0` disables it). For example,
`$env:UNO_MAX_UPLOAD_BYTES = "104857600"` sets 100 MiB in PowerShell. The UI reads
the configured limit from the server. Available temporary disk space, RAM, and
processing time still constrain practical file sizes.

PDFs have no fixed page-count cap. `UNO_PDF_DPI` controls rendering resolution
(default 150; range 36–600); unusually large pages are scaled down to keep each
raster within 25 million pixels. Image uploads retain the 25-million-pixel check.
Password-protected PDFs require an unlocked copy. All pages go through the OCR
model, including PDFs with embedded text. Results contain page labels and a total
inference time excluding model loading and PDF rendering. A failed page fails the
request with its page number; partial results are not returned. Large PDFs can
take a long time; this version returns results after all pages finish.

## Quick start

This Windows workspace has Python 3.12.10 in `.tools/python312` and a virtual
environment in `env`. Use it directly without changing your system Python:

```powershell
.\env\Scripts\python.exe --version
.\env\Scripts\python.exe run.py --device cpu
```

Optional PowerShell activation: `.\env\Scripts\Activate.ps1`. In your IDE, select
`env\Scripts\python.exe` as the Python interpreter. Keep `.tools/python312`:
the virtual environment depends on that base runtime. The launcher installs
application dependencies on first use; weights download on the first OCR request.

Install **Python 3.12** (with pip and venv) and **Git**, and add them to PATH.
From this project directory:

```sh
python run.py
```

Open http://127.0.0.1:8000. The launcher checks `nvidia-smi -L`, creates `env`,
clones the upstream repository, installs the selected dependencies, and starts
one uvicorn worker. Override detection with `python run.py --device cpu` or
`python run.py --device cuda`. Use `--setup-only` to stop before serving;
`--skip-install` to reuse installed dependencies; `--port 8001` to change ports.

CPU supports testing the application, upload handling, and device display.
**Successful CPU model loading/inference is not guaranteed**: upstream uses
explicit CUDA tensor operations. Failures appear in the UI with details and a
server traceback. A 16 GB NVIDIA GPU is the target for later validation, not a
verified memory guarantee. CUDA bfloat16 support and sufficient free VRAM matter.

## Manual CPU setup (Windows PowerShell)

```powershell
python -m venv env
.\env\Scripts\python.exe -m pip install -r requirements-cpu.txt
.\env\Scripts\python.exe run.py --device cpu --setup-only --skip-install
.\env\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

## Manual CUDA setup (Linux)

Use Python 3.12 and an NVIDIA driver compatible with the PyTorch CUDA 12.9 build.
`nvidia-smi` must work. Installing a CUDA wheel does not install a system driver.

```sh
python3.12 -m venv env
env/bin/python -m pip install -r requirements-cuda.txt
env/bin/python run.py --device cuda --setup-only --skip-install
env/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

For Linux CPU, substitute `requirements-cpu.txt` and `--device cpu`. For Windows
CUDA, use the Windows commands with `requirements-cuda.txt` and `--device cuda`.
When changing profiles, reinstall the corresponding requirements and restart.
Runtime device detection uses `torch.cuda.is_available()`, independently of the
launcher's dependency choice. Do not use multiple workers: each loads its own model.

## Model downloads and configuration

Weights are **not stored in this repository**. On the first OCR request,
`AutoTokenizer.from_pretrained()` and `AutoModel.from_pretrained()` download the
model from Hugging Face, normally cached beneath `~/.cache/huggingface` (the user
profile on Windows). Set `HF_HOME` before starting to choose another cache disk.
The UI and `/api/system-info` do not trigger downloads. Internet access and enough
disk/RAM are required on first use. Load start/finish are logged to the terminal.

The model requires `trust_remote_code=True`, executing code from the model repo.
`UNO_MODEL_REVISION` selects a Hugging Face revision (default `main`); set a reviewed
commit for reproducible experiments. `UNO_MAX_LENGTH` sets the total generation
sequence limit, default 4096, accepted range 1024–32768. Longer documents may be
truncated at the limit; raising it can increase latency and memory requirements.

Setup uses an ignored shallow clone at `vendor/unlimited-ocr`, not a submodule:
this works in a downloaded project without a parent Git repository. Existing
checkouts are retained without pulling. The clone is an upstream reference;
Transformers loads executable model code and weights from Hugging Face separately.

## Documentation and tests

- [Roadmap and acceptance criteria](docs/ROADMAP.md)
- [Architecture and API contract](docs/ARCHITECTURE.md)
- [Validation evidence and remaining checks](docs/VALIDATION.md)
- [Contributor/agent instructions](AGENTS.md)
- [Original project brief](unocrprompt.md)

Tests do not download a model or require PyTorch:

```sh
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
node --check frontend/app.js
```

Node is optional and used only for JavaScript syntax checking. See the validation
record before treating the implementation as hardware verified.

After updating application code, restart the server (Ctrl+C in its terminal, then
`env\Scripts\python.exe run.py --skip-install`) and reload the browser. The local
UI uses versioned asset URLs and no-store headers to keep HTML and JavaScript in
sync. If an old image-only validation message remains, use Ctrl+Shift+R once.
PDF selection shows a filename and summary; it does not embed a PDF page viewer.
Run `node --test tests/frontend.test.cjs` for PDF selection regression tests.
