"""Business logic layer – thin wrappers over db queries."""

from .db import (
    GPU,
    load_gpu_list,
    get_gpu,
    avg_price_period,
    lowest_listing,
    price_history as db_price_history,
    filtered_listings,
    listing_count,
    active_listing_count,
    gpu_listing_counts,
    last_updated,
)

# Cached GPU list (refreshed on import / app start)
GPU_LIST: list[GPU] = load_gpu_list()
_GPU_MAP: dict[str, GPU] = {g.id: g for g in GPU_LIST}


def refresh_gpu_cache():
    global GPU_LIST, _GPU_MAP
    GPU_LIST = load_gpu_list()
    _GPU_MAP = {g.id: g for g in GPU_LIST}


# ── Scatter data ──────────────────────────────────────────────────────

def scatter_points(metric: str = "vram", days: int | None = 30) -> list[dict]:
    points = []
    for gpu in GPU_LIST:
        avg = avg_price_period(gpu.id, days)
        if avg <= 0:
            continue
        low = lowest_listing(gpu.id)
        points.append({
            "quality": gpu.vram if metric == "vram" else gpu.tokens_sec,
            "price": avg,
            "gpu": gpu.name,
            "gpu_id": gpu.id,
            "vram": gpu.vram,
            "tokens": gpu.tokens_sec,
            "tokens_tested": gpu.tokens_tested,
            "lowest": low,
        })
    return points


# ── Filtered results (public) ────────────────────────────────────────

def filtered_results(
    *,
    min_vram: int = 0,
    min_tokens: float = 0,
    max_price: int = 999999,
    search: str = "",
    sort_by: str = "timestamp",
    order: str = "desc",
    active_only: bool = False,
    limit: int = 500,
) -> list[dict]:
    gpu_ids = [g.id for g in GPU_LIST if g.vram >= min_vram and g.tokens_sec >= min_tokens] or None
    rows = filtered_listings(
        gpu_ids=gpu_ids,
        min_price=0,
        max_price=max_price,
        search=search,
        active_only=active_only,
        sort_by=sort_by,
        order=order,
        limit=limit,
    )
    return [
        {
            "gpu": r["gpu_name"],
            "gpu_id": r["gpu_id"],
            "title": r["title"],
            "price": r["price"],
            "link": r["link"],
            "timestamp": r["timestamp"],
            "active": bool(r["active"]),
            "vram": r["vram"],
            "tokens": r["tokens_sec"],
        }
        for r in rows
    ]


# ── Stats ─────────────────────────────────────────────────────────────

def data_stats() -> dict:
    counts = gpu_listing_counts()
    return {
        "total_results": listing_count(),
        "active_results": active_listing_count(),
        "gpu_counts": counts,
        "last_updated": last_updated(),
        "tracked_gpus": len(GPU_LIST),
    }


# ── Price history ─────────────────────────────────────────────────────

def price_history(gpu_id: str, agg: str = "min", span: str = "30d"):
    return db_price_history(gpu_id, agg=agg, span=span)
