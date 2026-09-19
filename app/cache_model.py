"""Cache repository files without constructing a CPU or GPU model."""
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import time

from app.config import MODEL_ID, MODEL_REVISION, ROOT


def cache_model():
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    from huggingface_hub import snapshot_download
    from huggingface_hub.constants import HF_HUB_CACHE

    cache = Path(HF_HUB_CACHE)
    marker = ROOT / "env" / ".model-cache.json"
    key = [MODEL_ID, MODEL_REVISION, str(cache.resolve())]
    try:
        saved = json.loads(marker.read_text(encoding="utf-8"))
        if saved["key"] == key and saved["files"] and all(
            Path(name).is_file() and Path(name).stat().st_size == size
            for name, size in saved["files"].items()
        ):
            print("Model cache already complete; skipping download.", flush=True)
            return
    except (OSError, ValueError, KeyError, TypeError):
        pass
    drive = cache
    while not drive.exists():
        drive = drive.parent
    free = shutil.disk_usage(drive).free
    if free < 15 * 1024**3:
        raise RuntimeError(f"Model cache drive needs at least 15 GiB free; {free / 1024**3:.1f} GiB available at {drive}")
    print(f"Caching {MODEL_ID} (about 6-7 GB on first run) at {cache}. Downloads resume on retry.", flush=True)
    for attempt in range(1, 4):
        try:
            snapshot = Path(snapshot_download(repo_id=MODEL_ID, revision=MODEL_REVISION, cache_dir=str(cache)))
            files = {str(p): p.stat().st_size for p in snapshot.rglob("*") if p.is_file()}
            if not files or not any(name.endswith(".safetensors") for name in files):
                raise RuntimeError("Downloaded snapshot does not contain safetensors weights")
            marker.parent.mkdir(parents=True, exist_ok=True)
            temporary = marker.with_suffix(".tmp")
            temporary.write_text(json.dumps({"key": key, "files": files}), encoding="utf-8")
            temporary.replace(marker)
            print("Model cached successfully without allocating model memory.", flush=True)
            return
        except Exception as exc:
            print(f"Model download attempt {attempt}/3 failed: {exc}", file=sys.stderr, flush=True)
            if attempt == 3:
                raise
            time.sleep(attempt * 2)


def main():
    try:
        cache_model()
        return 0
    except Exception:
        logging.exception("Model caching failed; fix the error above and rerun setup.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
