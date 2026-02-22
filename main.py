from dataclasses import dataclass

@dataclass
class GPU:
    """GPU specifications."""
    name: str
    tokens_sec: float
    vram: int
    search_queries: list[str]
    tokens_tested: bool = False  # is tokens/s tested or estimated based on similar models


GPU_LIST = [
    # Existing GPUs (renamed without VRAM)
    GPU("RTX 3070", 70.94, 8, ["RTX 3070", "3070"], tokens_tested=True),
    GPU("RTX 3080", 106.40, 10, ["RTX 3080", "3080"], tokens_tested=True),
    GPU("RTX 3080 Ti", 106.71, 12, ["RTX 3080 Ti", "RTX 3080ti", "3080 Ti"], tokens_tested=True),
    GPU("RTX 4070 Ti", 82.21, 12, ["RTX 4070 Ti", "RTX 4070ti", "4070 Ti"], tokens_tested=True),
    GPU("RTX 4080", 106.22, 16, ["RTX 4080", "4080"], tokens_tested=True),
    GPU("RTX 4000 Ada", 58.59, 20, ["RTX 4000 Ada", "4000 Ada"], tokens_tested=True),
    GPU("RTX 3090", 111.74, 24, ["RTX 3090", "3090"], tokens_tested=True),
    GPU("RTX 4090", 127.74, 24, ["RTX 4090", "4090"], tokens_tested=True),
    GPU("RTX 5000 Ada", 89.87, 32, ["RTX 5000 Ada", "5000 Ada"], tokens_tested=True),
    GPU("RTX A6000", 102.22, 48, ["RTX A6000", "A6000"], tokens_tested=True),
    GPU("RTX 6000 Ada", 130.99, 48, ["RTX 6000 Ada", "6000 Ada"], tokens_tested=True),
    GPU("A40", 88.95, 48, ["A40"], tokens_tested=True),
    GPU("L40S", 113.60, 48, ["L40S", "L40"], tokens_tested=True),
    GPU("A100 PCIe", 138.31, 80, ["A100 PCIe", "A100"], tokens_tested=True),
    GPU("A100 SXM", 133.38, 80, ["A100 SXM"], tokens_tested=True),

    # -------------------------
    # Added GPUs (estimated)
    # -------------------------

    # RTX 20‑series (Turing)
    GPU("RTX 2060_EST", 28.0, 6, ["RTX 2060", "2060"], tokens_tested=False),
    GPU("RTX 2070_EST", 38.0, 8, ["RTX 2070", "2070"], tokens_tested=False),
    GPU("RTX 2080_EST", 52.0, 8, ["RTX 2080", "2080"], tokens_tested=False),
    GPU("RTX 2080 Ti_EST", 65.0, 11, ["RTX 2080 Ti", "2080 Ti"], tokens_tested=False),

    # RTX 30‑series missing cards
    GPU("RTX 3060_EST", 48.0, 12, ["RTX 3060", "3060"], tokens_tested=False),
    GPU("RTX 3060 Ti_EST", 60.0, 8, ["RTX 3060 Ti", "3060 Ti"], tokens_tested=False),
    GPU("RTX 3070 Ti_EST", 75.0, 8, ["RTX 3070 Ti", "3070 Ti"], tokens_tested=False),
    GPU("RTX 3080 12GB_EST", 112.0, 12, ["RTX 3080 12GB", "3080 12GB"], tokens_tested=False),
    GPU("RTX 3090 Ti_EST", 118.0, 24, ["RTX 3090 Ti", "3090 Ti"], tokens_tested=False),

    # RTX 40‑series missing cards
    GPU("RTX 4060_EST", 40.0, 8, ["RTX 4060", "4060"], tokens_tested=False),
    GPU("RTX 4060 Ti_EST", 52.0, 8, ["RTX 4060 Ti", "4060 Ti"], tokens_tested=False),
    GPU("RTX 4070_EST", 70.0, 12, ["RTX 4070", "4070"], tokens_tested=False),
    GPU("RTX 4070 Super_EST", 78.0, 12, ["RTX 4070 Super", "4070 Super"], tokens_tested=False),
    GPU("RTX 4070 Ti Super_EST", 92.0, 16, ["RTX 4070 Ti Super", "4070 Ti Super"], tokens_tested=False),
    GPU("RTX 4080 Super_EST", 112.0, 16, ["RTX 4080 Super", "4080 Super"], tokens_tested=False),

    # Workstation / datacenter missing cards
    GPU("RTX A4000_EST", 52.0, 16, ["RTX A4000", "A4000"], tokens_tested=False),
    GPU("RTX A5000_EST", 72.0, 24, ["RTX A5000", "A5000"], tokens_tested=False),
    GPU("RTX A4500_EST", 62.0, 20, ["RTX A4500", "A4500"], tokens_tested=False),
    GPU("RTX A5500_EST", 82.0, 24, ["RTX A5500", "A5500"], tokens_tested=False),
    GPU("A30_EST", 70.0, 24, ["A30"], tokens_tested=False),
    GPU("A10_EST", 55.0, 24, ["A10"], tokens_tested=False),
    GPU("T4_EST", 22.0, 16, ["T4"], tokens_tested=False),

    # New Ada workstation cards
    GPU("RTX 2000 Ada_EST", 32.0, 16, ["RTX 2000 Ada", "2000 Ada"], tokens_tested=False),
    GPU("RTX 3000 Ada_EST", 45.0, 24, ["RTX 3000 Ada", "3000 Ada"], tokens_tested=False),
]
