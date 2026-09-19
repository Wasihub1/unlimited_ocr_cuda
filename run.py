"""Idempotent dependency/cache setup followed by a single localhost server."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import venv
import webbrowser

ROOT = Path(__file__).resolve().parent


def command(args, **kwargs):
    """Stream native output to console/log while preserving the exit status."""
    with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, errors="replace", **kwargs) as process:
        for line in process.stdout:
            print(line, end="", flush=True)
        if process.wait():
            raise RuntimeError(f"{args[0]} exited with code {process.returncode}; see output above")


def dependency_profile(device):
    if device != "auto":
        return device
    smi = shutil.which("nvidia-smi")
    return "cuda" if smi and subprocess.run([smi, "-L"], capture_output=True).returncode == 0 else "cpu"


def ensure_environment():
    folder = ROOT / "env"
    python = folder / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        print("Creating virtual environment...", flush=True)
        venv.EnvBuilder(with_pip=True).create(folder)
    return python


def install_dependencies(python, device):
    files = [ROOT / "requirements-common.txt", ROOT / f"requirements-{device}.txt"]
    digest = hashlib.sha256(device.encode() + b"".join(p.read_bytes() for p in files)).hexdigest()
    stamp = ROOT / "env" / ".requirements.stamp"
    if stamp.exists() and stamp.read_text().strip() == digest:
        print("Requirements unchanged; skipping pip install.", flush=True)
        return
    command([str(python), "-m", "pip", "install", "-r", str(files[0]), "-r", str(files[1])])
    stamp.write_text(digest, encoding="utf-8")


def open_when_ready(url, stop):
    deadline = time.monotonic() + 120
    while not stop.is_set() and time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url + "/api/system-info", timeout=2) as response:
                if response.status == 200 and not stop.is_set():
                    webbrowser.open(url)
                    return
        except OSError:
            pass
        stop.wait(0.5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--setup-only", action="store_true")
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if sys.version_info < (3, 10) or sys.version_info >= (3, 14):
        parser.error("Use Python 3.10-3.13 (3.12 recommended).")
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535")
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    step = "environment"
    try:
        python = ensure_environment()
        step = "vendor checkout"
        vendor = ROOT / "vendor" / "unlimited-ocr"
        if not vendor.exists():
            if not shutil.which("git"):
                raise RuntimeError("Install Git and add it to PATH.")
            vendor.parent.mkdir(exist_ok=True)
            command(["git", "clone", "--depth", "1", "https://github.com/baidu/unlimited-ocr", str(vendor)])
        elif not (vendor / ".git").exists():
            raise RuntimeError("vendor/unlimited-ocr is not a Git checkout; inspect it before retrying.")
        step = "dependencies"
        device = dependency_profile(args.device)
        print(f"Dependency profile: {device}. Runtime CUDA is checked by PyTorch.", flush=True)
        if not args.skip_install:
            install_dependencies(python, device)
        step = "model cache"
        if args.force_download or (device == "cuda" and (args.setup_only or not args.skip_install)):
            command([str(python), "-m", "app.cache_model"], cwd=ROOT)
        elif device == "cpu":
            print("No NVIDIA GPU detected: skipping model download. Use --force-download to cache it anyway.", flush=True)
        if args.setup_only:
            print("Setup complete.", flush=True)
            return 0
        step = "server"
        url = f"http://127.0.0.1:{args.port}"
        print(f"\nOpen {url}\n", flush=True)
        if Path(sys.prefix).resolve() != (ROOT / "env").resolve():
            forwarded = [str(python), str(ROOT / "run.py"), "--skip-install", "--port", str(args.port), "--device", device]
            if args.no_browser:
                forwarded.append("--no-browser")
            return subprocess.call(forwarded, cwd=ROOT)
        import uvicorn
        stop = threading.Event()
        if not args.no_browser:
            threading.Thread(target=open_when_ready, args=(url, stop), daemon=True).start()
        try:
            uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, workers=1)
        finally:
            stop.set()
        return 0
    except (RuntimeError, OSError, ImportError) as exc:
        print(f"Setup failed at step {step}: {exc}", file=sys.stderr, flush=True)
        return 1


class Tee:
    def __init__(self, console, logfile):
        self.console, self.logfile = console, logfile

    def write(self, text):
        self.console.write(text)
        self.logfile.write(text)
        self.flush()

    def flush(self):
        self.console.flush()
        self.logfile.flush()

    def isatty(self):
        return False


if __name__ == "__main__":
    (ROOT / "logs").mkdir(exist_ok=True)
    original = sys.stdout, sys.stderr
    # PowerShell owns the same log during setup; avoid concurrent file handles.
    if os.environ.get("UNO_SETUP_TRANSCRIPT") == "1":
        sys.exit(main())
    with (ROOT / "logs" / "setup.log").open("a", encoding="utf-8") as logfile:
        sys.stdout, sys.stderr = Tee(sys.stdout, logfile), Tee(sys.stderr, logfile)
        try:
            code = main()
        finally:
            sys.stdout, sys.stderr = original
    sys.exit(code)
