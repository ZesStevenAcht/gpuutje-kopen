"""GPU price tracker for Marktplaats."""

from datetime import datetime
from dataclasses import dataclass


@dataclass
class GPU:
    """GPU specifications."""
    name: str
    tokens_sec: float
    vram: int
    search_queries: list[str]


# GPU list with search variations to handle different spellings/capitalizations
GPU_LIST = [
    GPU("RTX 3070 8GB", 70.94, 8, ["RTX 3070", "3070"]),
    GPU("RTX 3080 10GB", 106.40, 10, ["RTX 3080", "3080"]),
    GPU("RTX 3080 Ti 12GB", 106.71, 12, ["RTX 3080 Ti", "RTX 3080ti", "3080 Ti"]),
    GPU("RTX 4070 Ti 12GB", 82.21, 12, ["RTX 4070 Ti", "RTX 4070ti", "4070 Ti"]),
    GPU("RTX 4080 16GB", 106.22, 16, ["RTX 4080", "4080"]),
    GPU("RTX 4000 Ada 20GB", 58.59, 20, ["RTX 4000 Ada", "4000 Ada"]),
    GPU("RTX 3090 24GB", 111.74, 24, ["RTX 3090", "3090"]),
    GPU("RTX 4090 24GB", 127.74, 24, ["RTX 4090", "4090"]),
    GPU("RTX 5000 Ada 32GB", 89.87, 32, ["RTX 5000 Ada", "5000 Ada"]),
    GPU("RTX A6000 48GB", 102.22, 48, ["RTX A6000", "A6000"]),
    GPU("RTX 6000 Ada 48GB", 130.99, 48, ["RTX 6000 Ada", "6000 Ada"]),
    GPU("A40 48GB", 88.95, 48, ["A40"]),
    GPU("L40S 48GB", 113.60, 48, ["L40S", "L40"]),
    GPU("A100 PCIe 80GB", 138.31, 80, ["A100 PCIe", "A100"]),
    GPU("A100 SXM 80GB", 133.38, 80, ["A100 SXM"]),
]
