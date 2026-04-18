"""Admin / control panel routes."""

from dataclasses import asdict
from flask import Blueprint, render_template, request, jsonify
from ..db import (
    GPU,
    load_gpu_list,
    add_gpu,
    update_gpu,
    delete_gpu,
    next_gpu_id,
    gpu_breakdown,
    browse_listings,
    update_listing,
    delete_listing,
    delete_listings_by_gpu,
    listing_count,
    active_listing_count,
    last_updated,
    browse_outliers,
    restore_outlier,
    delete_outlier,
    outlier_count,
    sweep_outliers,
    revalidate_listings,
    browse_restored_listings,
    unrestore_listing,
)
from ..services import data_stats, refresh_gpu_cache
from ..search_worker import run_search_cycle, SEARCH_INTERVAL, _stop_event, get_search_interval, set_search_interval
import logging
import threading

log = logging.getLogger(__name__)
admin = Blueprint("admin", __name__)


@admin.route("/")
def dashboard():
    return render_template("admin.html")


# ── Stats ─────────────────────────────────────────────────────────────

@admin.route("/api/stats")
def stats():
    s = data_stats()
    s["search_interval_min"] = get_search_interval() / 60
    s["search_interval_sec"] = get_search_interval()
    s["worker_running"] = not _stop_event.is_set()
    s["outlier_count"] = outlier_count()
    return jsonify(s)


# ── Worker control ────────────────────────────────────────────────────

@admin.route("/api/trigger-search", methods=["POST"])
def trigger_search():
    threading.Thread(target=run_search_cycle, daemon=True).start()
    return jsonify({"status": "started"})


@admin.route("/api/search-interval", methods=["PUT"])
def update_search_interval():
    body = request.get_json(force=True)
    try:
        seconds = int(body["seconds"])
        set_search_interval(seconds)
        return jsonify({"status": "updated", "seconds": get_search_interval()})
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400


# ── GPU CRUD ──────────────────────────────────────────────────────────

@admin.route("/api/gpus")
def list_gpus():
    return jsonify([asdict(g) for g in load_gpu_list()])


@admin.route("/api/gpus", methods=["POST"])
def create_gpu():
    body = request.get_json(force=True)
    try:
        gpu = GPU(
            id=body.get("id") or next_gpu_id(body["name"]),
            name=body["name"],
            tokens_sec=float(body.get("tokens_sec", 0)),
            vram=int(body.get("vram", 0)),
            search_queries=body.get("search_queries", []),
            tokens_tested=bool(body.get("tokens_tested", False)),
        )
        add_gpu(gpu)
        refresh_gpu_cache()
        return jsonify({"status": "created", "gpu": asdict(gpu)}), 201
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400


@admin.route("/api/gpus/<gpu_id>", methods=["PUT"])
def edit_gpu(gpu_id: str):
    body = request.get_json(force=True)
    try:
        gpu = update_gpu(gpu_id, body)
        refresh_gpu_cache()
        return jsonify({"status": "updated", "gpu": asdict(gpu)})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@admin.route("/api/gpus/<gpu_id>", methods=["DELETE"])
def remove_gpu(gpu_id: str):
    try:
        delete_gpu(gpu_id)
        refresh_gpu_cache()
        return jsonify({"status": "deleted"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


# ── GPU breakdown ─────────────────────────────────────────────────────

@admin.route("/api/gpu-breakdown")
def api_gpu_breakdown():
    rows = gpu_breakdown()
    return jsonify([
        {
            "gpu_id": r["id"],
            "gpu": r["name"],
            "vram": r["vram"],
            "tokens_sec": r["tokens_sec"],
            "total_listings": r["total"],
            "active_listings": r["active"],
            "min_price": r["min_price"],
            "max_price": r["max_price"],
        }
        for r in rows
    ])


# ── Results browser / editor ──────────────────────────────────────────

@admin.route("/api/results")
def api_browse_results():
    rows = browse_listings(
        gpu_filter=request.args.get("gpu", ""),
        search=request.args.get("search", ""),
        min_price=request.args.get("min_price", 0, type=float),
        max_price=request.args.get("max_price", 999999, type=float),
        active_only=request.args.get("active_only", "") == "true",
        sort_by=request.args.get("sort_by", "timestamp"),
        order=request.args.get("order", "desc"),
        limit=request.args.get("limit", 200, type=int),
    )
    return jsonify(rows)


@admin.route("/api/results/<int:pk>", methods=["PUT"])
def edit_result(pk: int):
    body = request.get_json(force=True)
    updated = update_listing(pk, body)
    if updated is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"status": "updated", "result": updated})


@admin.route("/api/results/<int:pk>", methods=["DELETE"])
def remove_result(pk: int):
    if delete_listing(pk):
        return jsonify({"status": "deleted"})
    return jsonify({"error": "Not found"}), 404


@admin.route("/api/results/gpu/<gpu_id>", methods=["DELETE"])
def remove_results_by_gpu(gpu_id: str):
    count = delete_listings_by_gpu(gpu_id)
    return jsonify({"status": "deleted", "count": count})


# ── Outliers ──────────────────────────────────────────────────────────

@admin.route("/api/outliers")
def api_outliers():
    rows = browse_outliers(
        gpu_filter=request.args.get("gpu", ""),
        sort_by=request.args.get("sort_by", "moved_at"),
        order=request.args.get("order", "desc"),
        limit=request.args.get("limit", 200, type=int),
    )
    return jsonify(rows)


@admin.route("/api/outliers/<int:pk>/restore", methods=["POST"])
def api_restore_outlier(pk: int):
    if restore_outlier(pk):
        return jsonify({"status": "restored"})
    return jsonify({"error": "Not found"}), 404


@admin.route("/api/outliers/<int:pk>", methods=["DELETE"])
def api_delete_outlier(pk: int):
    if delete_outlier(pk):
        return jsonify({"status": "deleted"})
    return jsonify({"error": "Not found"}), 404


@admin.route("/api/outliers/sweep", methods=["POST"])
def api_sweep_outliers():
    result = sweep_outliers()
    return jsonify({"status": "done", **result})


@admin.route("/api/revalidate", methods=["POST"])
def api_revalidate():
    result = revalidate_listings()
    return jsonify({"status": "done", **result})


@admin.route("/api/restored")
def api_restored():
    rows = browse_restored_listings(
        gpu_filter=request.args.get("gpu", ""),
        limit=request.args.get("limit", 200, type=int),
    )
    return jsonify(rows)


@admin.route("/api/restored/<int:pk>/unrestore", methods=["POST"])
def api_unrestore(pk: int):
    if unrestore_listing(pk):
        return jsonify({"status": "unflagged"})
    return jsonify({"error": "Not found"}), 404
