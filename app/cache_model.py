"""Populate the Transformers cache during setup, without allocating GPU memory."""
import logging
import sys

from app.config import MODEL_ID, MODEL_REVISION


def main():
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer

        print("Downloading model weights, this may take several minutes...", flush=True)
        AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION, trust_remote_code=True)
        model = AutoModel.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION, trust_remote_code=True,
            use_safetensors=True, torch_dtype=torch.bfloat16,
        )
        del model
        print("Model cached successfully.", flush=True)
        return 0
    except Exception:
        logging.exception("Model caching failed. Check network access, free RAM/disk, and model dependencies; rerun setup.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
