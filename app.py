"""Flask web app for GPU price tracker."""

import json
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta

from main import GPU_LIST
from storage import load_results, get_results_by_gpu, get_latest_listings
from analytics import calc_price_history, get_avg_price_period
from search_worker import start_worker_thread


app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# Start search worker only in main process (not in Flask reloader)
def _init_worker():
    """Initialize worker thread (called once on startup)."""
    import os
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_worker_thread()

_init_worker()


@app.route("/")
def index():
    """Main page."""
    return render_template("index.html")


@app.route("/api/gpus")
def api_gpus():
    """Get list of all GPUs."""
    return jsonify([
        {
            "name": gpu.name,
            "vram": gpu.vram,
            "tokens_sec": gpu.tokens_sec,
        }
        for gpu in GPU_LIST
    ])


@app.route("/api/price-history/<gpu_name>")
def api_price_history(gpu_name):
    """Get price history for a GPU."""
    # aggregation: agg=min|avg, period=day|week|month
    agg = request.args.get("agg", "min")
    period = request.args.get("period", "day")

    results = get_results_by_gpu(gpu_name)
    history = calc_price_history(results, agg=agg, period=period)

    return jsonify({
        "dates": [h[0] for h in history],
        "prices": [h[1] for h in history],
    })


@app.route("/api/scatter-data")
def api_scatter_data():
    """Get scatter data for VRAM/Tokens vs avg price."""
    days_str = request.args.get("days")
    metric = request.args.get("metric", "vram")  # vram or tokens
    
    days = None if days_str == "all" else int(days_str) if days_str else 7
    
    points = []
    
    for gpu in GPU_LIST:
        results = get_results_by_gpu(gpu.name)
        if not results:
            continue
        
        avg_price = get_avg_price_period(results, days)
        if avg_price <= 0:
            continue
        # quality is VRAM or tokens (to maximize), price is avg_price (to minimize)
        quality = gpu.vram if metric == "vram" else gpu.tokens_sec

        # Find lowest-priced listing link for this GPU
        lowest = None
        for r in results:
            p = r.get("price")
            if not isinstance(p, (int, float)):
                continue
            if lowest is None or p < lowest["price"]:
                lowest = {"price": p, "link": r.get("link"), "title": r.get("title"), "timestamp": r.get("timestamp")}

        points.append({
            "quality": quality,
            "price": avg_price,
            "gpu": gpu.name,
            "vram": gpu.vram,
            "tokens": gpu.tokens_sec,
            "tokens_tested": gpu.tokens_tested,
            "lowest": lowest,
        })
    
    return jsonify({
        "points": points,
    })


@app.route("/api/results")
def api_results():
    """Get latest search results with optional filtering."""
    min_vram = request.args.get("min_vram", 0, type=int)
    min_tokens = request.args.get("min_tokens", 0, type=float)
    max_price = request.args.get("max_price", 999999, type=int)
    search = request.args.get("search", "").lower()
    
    results = []
    seen = set()  # Avoid duplicates
    
    for gpu in GPU_LIST:
        if gpu.vram < min_vram or gpu.tokens_sec < min_tokens:
            continue
        
        gpu_results = get_results_by_gpu(gpu.name)
        
        # Get unique latest listings
        for r in gpu_results:
            key = (gpu.name, r["title"], r["price"])
            if key in seen:
                continue
            seen.add(key)
            
            price = r.get("price", 0)
            if not isinstance(price, (int, float)) or price > max_price:
                continue
            
            title_lower = r["title"].lower() if r["title"] else ""
            if search and search not in title_lower:
                continue
            
            results.append({
                "gpu": gpu.name,
                "title": r["title"],
                "price": price,
                "link": r["link"],
                "timestamp": r["timestamp"],
                "vram": gpu.vram,
                "tokens": gpu.tokens_sec,
            })
    
    # Sort by timestamp descending
    # Optional sorting
    sort_by = request.args.get("sort_by", "timestamp")  # price, type, vram, tokens, timestamp
    order = request.args.get("order", "desc")  # asc or desc

    def sort_key(r):
        if sort_by == "price":
            return r.get("price", 0)
        if sort_by == "type":
            return r.get("gpu", "")
        if sort_by == "vram":
            return r.get("vram", 0)
        if sort_by == "tokens":
            return r.get("tokens", 0)
        # default timestamp
        return r.get("timestamp", "")

    reverse = order != "asc"
    results.sort(key=sort_key, reverse=reverse)
    
    # Limit to 500 results
    return jsonify(results[:500])


@app.route("/api/stats")
def api_stats():
    """Get statistics about the data."""
    data = load_results()
    total_results = len(data["results"])
    
    gpu_counts = {}
    for r in data["results"]:
        gpu = r["gpu_name"]
        gpu_counts[gpu] = gpu_counts.get(gpu, 0) + 1
    
    return jsonify({
        "total_results": total_results,
        "gpu_counts": gpu_counts,
        "last_updated": data.get("updated"),
    })


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)
