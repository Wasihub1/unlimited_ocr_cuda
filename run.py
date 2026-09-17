"""Bootstrap the vendor checkout and local environment, then start the app."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--setup-only", action="store_true")
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if sys.version_info < (3, 10) or sys.version_info >= (3, 14):
        parser.error("Use Python 3.10-3.13 (3.12 recommended).")
    if not shutil.which("git"):
        parser.error("Install Git and add it to PATH.")
    vendor = ROOT / "vendor" / "unlimited-ocr"
    if not vendor.exists():
        vendor.parent.mkdir(exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/baidu/unlimited-ocr", str(vendor)], check=True)
    elif not (vendor / ".git").exists():
        parser.error("vendor/unlimited-ocr exists but is not a Git checkout; inspect it before retrying.")
    env = ROOT / "env"
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(env)
    device = args.device
    if device == "auto":
        smi = shutil.which("nvidia-smi")
        device = "cuda" if smi and subprocess.run([smi, "-L"], capture_output=True).returncode == 0 else "cpu"
    print(f"Dependency profile: {device}. Runtime device is detected by PyTorch.", flush=True)
    if not args.skip_install:
        subprocess.run([str(python), "-m", "pip", "install", "-r", str(ROOT / f"requirements-{device}.txt")], check=True)
    if not args.setup_only:
        subprocess.run([str(python), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(args.port), "--workers", "1"], cwd=ROOT, check=True)


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"Setup/start failed: {exc}", file=sys.stderr)
        sys.exit(1)
