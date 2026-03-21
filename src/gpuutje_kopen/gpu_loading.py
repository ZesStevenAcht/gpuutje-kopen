from dataclasses import dataclass, asdict
import json
from typing import List

@dataclass
class GPU:
    """GPU specifications."""
    name: str
    tokens_sec: float
    vram: int
    search_queries: List[str]
    tokens_tested: bool = False  # is tokens/s tested or estimated based on similar models

def load_gpu_list(json_path: str = "gpu_list.json") -> List[GPU]:
    """Load GPU list from a JSON file."""
    with open(json_path, "r") as f:
        data = json.load(f)
    return [GPU(**gpu) for gpu in data]

# Example usage:
# GPU_LIST = load_gpu_list()
