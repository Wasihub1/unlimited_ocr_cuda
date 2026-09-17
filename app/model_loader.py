"""Load once during startup; expose readiness and refuse OCR before ready."""
import logging
import threading
import time

from app.config import MAX_LENGTH, MODEL_ID, MODEL_REVISION
from app.device import detect_device

log = logging.getLogger(__name__)


class ModelError(RuntimeError):
    pass


class ModelBusy(ModelError):
    pass


class ModelService:
    def __init__(self):
        self._lock = threading.Lock()
        self._model = None
        self._tokenizer = None
        self.status = "loading"
        self.error = None

    def initialize(self):
        with self._lock:
            if self.status == "ready":
                return
            self.status, self.error = "loading", None
            try:
                self._load()
                self.status = "ready"
                log.info("Model loaded and ready")
            except Exception as exc:
                self.status, self.error = "error", str(exc)
                log.exception("Startup model loading failed; run setup.ps1 to populate the cache")

    def _load(self):
        if self._model is not None:
            return
        from transformers import AutoModel, AutoTokenizer

        hardware = detect_device()
        log.info("Loading cached %s on %s", MODEL_ID, hardware.device)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION, trust_remote_code=True, local_files_only=True)
        # A future CPU fallback belongs here AND in upstream image/attention code.
        # eager attention alone cannot fix upstream's explicit .cuda() calls.
        model = AutoModel.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION, trust_remote_code=True,
            use_safetensors=True, torch_dtype=hardware.dtype,
            local_files_only=True,
        ).eval().to(hardware.device)
        self._tokenizer, self._model = tokenizer, model
        log.info("Model loading finished.")

    def infer(self, image_path, output_path):
        if self.status != "ready":
            raise ModelError(self.error or "Model is loading, please wait...")
        if not self._lock.acquire(blocking=False):
            raise ModelBusy("Another OCR request is running. Try again after it finishes.")
        try:
            import torch

            started = time.perf_counter()
            config = self._model.config
            window = getattr(config, "sliding_window", None)
            linear_reset = torch.nn.Linear.reset_parameters
            norm_reset = torch.nn.LayerNorm.reset_parameters
            try:
                with torch.inference_mode():
                    result = self._model.infer(
                        self._tokenizer, prompt="<image>document parsing.",
                        image_file=str(image_path), output_path=str(output_path),
                        base_size=1024, image_size=640, crop_mode=True,
                        eval_mode=True, save_results=False, max_length=MAX_LENGTH,
                        no_repeat_ngram_size=35, ngram_window=128,
                    )
            finally:
                # Upstream mutates these; restore even after failed generation.
                config.sliding_window = window
                torch.nn.Linear.reset_parameters = linear_reset
                torch.nn.LayerNorm.reset_parameters = norm_reset
            if not isinstance(result, str):
                raise RuntimeError("Upstream infer(eval_mode=True) did not return text.")
            return {"text": result, "inference_seconds": round(time.perf_counter() - started, 3)}
        except Exception as exc:
            log.exception("Model loading or inference failed")
            hint = (
                "CPU execution is experimental: upstream uses CUDA-only operations. "
                "Use a compatible NVIDIA CUDA machine for inference."
                if detect_device().device == "cpu" else
                "Check available VRAM, the CUDA driver, and Hugging Face connectivity."
            )
            raise ModelError(f"Unlimited-OCR could not complete the request. {hint} Details: {exc}") from exc
        finally:
            self._lock.release()


service = ModelService()
