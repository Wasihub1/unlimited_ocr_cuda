&nbsp;

Project: Unlimited-OCR Test UI

&nbsp;

Goal: Build a lightweight, clean local test application for Baidu's Unlimited-OCR&nbsp;

model (https://github.com/baidu/unlimited-ocr), with a FastAPI backend and a&nbsp;

minimal vanilla HTML/CSS/JS frontend. No Streamlit, no Gradio, no heavy frontend&nbsp;

framework (no React/Vue needed — plain HTML/CSS/JS is fine).

&nbsp;

Requirements:

&nbsp;

1\. Clone https://github.com/baidu/unlimited-ocr into vendor/unlimited-ocr as part&nbsp;

&nbsp;&nbsp;&nbsp;of the setup script (or as a git submodule — pick whichever is cleaner and&nbsp;

&nbsp;&nbsp;&nbsp;document the choice in README).

&nbsp;

2\. Folder structure:

&nbsp;&nbsp;&nbsp;\- app/ (FastAPI backend: main.py, model\_loader.py, device.py, config.py, routes/)

&nbsp;&nbsp;&nbsp;\- frontend/ (single-page HTML/CSS/JS: upload area, preview, run button, result&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;panel, device-status badge)

&nbsp;&nbsp;&nbsp;\- requirements-cpu.txt and requirements-cuda.txt (separate — torch CPU/CUDA&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;builds are different packages)

&nbsp;&nbsp;&nbsp;\- README.md with exact setup steps for both a non-CUDA dev laptop and a CUDA&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;machine, and a clear note that model weights are NOT stored in the repo —&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;they auto-download from Hugging Face on first run via transformers'&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;from\_pretrained(), cached in \~/.cache/huggingface

&nbsp;&nbsp;&nbsp;\- .gitignore excluding venv, \_\_pycache\_\_, model cache, any weight files

&nbsp;

3\. app/device.py — hardware auto-detection:

&nbsp;&nbsp;&nbsp;\- torch.cuda.is\_available() check

&nbsp;&nbsp;&nbsp;\- if True, get device name \+ total VRAM via torch.cuda.get\_device\_properties

&nbsp;&nbsp;&nbsp;\- return a resolved (device, dtype) pair: cuda→bfloat16, cpu→float32

&nbsp;&nbsp;&nbsp;\- expose this via GET /api/system-info so the frontend can display it

&nbsp;

4\. app/model\_loader.py:

&nbsp;&nbsp;&nbsp;\- Load baidu/Unlimited-OCR via AutoModel/AutoTokenizer with trust\_remote\_code=True

&nbsp;&nbsp;&nbsp;\- Use the device/dtype from device.py, lazy-load as a singleton (load once,&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;log start/finish clearly, since first load \= big download)

&nbsp;&nbsp;&nbsp;\- Wrap load/inference in try/except: on CPU, the model's custom code&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(deepencoder.py / modeling\_deepseekv2.py) may hit CUDA-only ops — catch this,&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;surface a clear readable error instead of a silent crash, and leave a code&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;comment marking where an eager-attention CPU fallback would go if needed

&nbsp;

5\. API endpoints:

&nbsp;&nbsp;&nbsp;\- GET  /api/system-info  → {device, device\_name, vram\_gb}

&nbsp;&nbsp;&nbsp;\- POST /api/ocr          → multipart image upload → runs model.infer(...) →&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;returns extracted text \+ inference time

&nbsp;&nbsp;&nbsp;\- GET  /                 → serves the frontend

&nbsp;

6\. Frontend (clean, minimal, single page):

&nbsp;&nbsp;&nbsp;\- Drag-and-drop / click-to-upload image area with preview

&nbsp;&nbsp;&nbsp;\- "Run OCR" button (disabled \+ spinner while running)

&nbsp;&nbsp;&nbsp;\- Result panel: extracted text \+ inference time

&nbsp;&nbsp;&nbsp;\- Small corner badge showing detected device (CPU / CUDA \+ VRAM), fetched from&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;/api/system-info on page load

&nbsp;

7\. Provide run.sh (or run.py) that: checks for nvidia-smi to decide which&nbsp;

&nbsp;&nbsp;&nbsp;requirements file to install, sets up venv if missing, installs deps, starts&nbsp;

&nbsp;&nbsp;&nbsp;uvicorn.

&nbsp;

Deliver the full project, ready to first run with&nbsp;

\`pip install \-r requirements-cpu.txt\` on a non-CUDA machine just to confirm the&nbsp;

app boots and the model loads (even slowly), and later with requirements-cuda.txt&nbsp;

on a 16GB VRAM machine.

&nbsp;