from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Hardware:
    device: str
    device_name: str
    vram_gb: float
    dtype: object


@lru_cache(maxsize=1)
def detect_device():
    import torch

    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        return Hardware("cuda", props.name, round(props.total_memory / 1024**3, 2), torch.bfloat16)
    return Hardware("cpu", "CPU", 0.0, torch.float32)
