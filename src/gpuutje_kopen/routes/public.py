"""Public-facing routes (main dashboard + data APIs)."""

import time
from collections import defaultdict
from flask import Blueprint, render_template, request, jsonify
from ..services import GPU_LIST, price_history, scatter_points, filtered_results, data_stats
from ..db import record_page_view

public = Blueprint("public", __name__)

# Simple in-memory rate limiter: max 1 page_view write per IP per second
_pv_last_write: dict[str, float] = defaultdict(float)
_PV_MIN_INTERVAL = 1.0  # seconds


@public.before_request
def track_page_view():
    """Record every non-static page hit (rate-limited)."""
    if request.path.startswith("/static"):
        return
    try:
        ip = request.remote_addr or ""
        now = time.monotonic()
        if now - _pv_last_write[ip] < _PV_MIN_INTERVAL:
            return
        _pv_last_write[ip] = now
        record_page_view(
            path=request.path,
            ip=ip,
            user_agent=(request.user_agent.string or "")[:256],
        )
    except Exception:
        pass  # never break the request over analytics


@public.route("/")
def index():
    return render_template("index.html")


@public.route("/test")
def test_page():
    return render_template("test.html")


@public.route("/api/gpus")
def api_gpus():
    return jsonify([{"id": g.id, "name": g.name, "vram": g.vram, "tokens_sec": g.tokens_sec} for g in GPU_LIST])


@public.route("/api/price-history/<gpu_id>")
def api_price_history(gpu_id):
    agg = request.args.get("agg", "min")
    span = request.args.get("span", "30d")
    history = price_history(gpu_id, agg=agg, span=span)
    return jsonify({"dates": [h[0] for h in history], "prices": [h[1] for h in history]})


@public.route("/api/scatter-data")
def api_scatter_data():
    days_str = request.args.get("days")
    metric = request.args.get("metric", "vram")
    if days_str == "all":
        days = None
    else:
        days = request.args.get("days", 30, type=int)
    return jsonify({"points": scatter_points(metric=metric, days=days)})


@public.route("/api/results")
def api_results():
    return jsonify(filtered_results(
        min_vram=request.args.get("min_vram", 0, type=int),
        min_tokens=request.args.get("min_tokens", 0, type=float),
        max_price=request.args.get("max_price", 999999, type=int),
        search=request.args.get("search", "").lower(),
        sort_by=request.args.get("sort_by", "timestamp"),
        order=request.args.get("order", "desc"),
    ))


@public.route("/api/stats")
def api_stats():
    return jsonify(data_stats())
