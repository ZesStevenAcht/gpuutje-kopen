"""Data storage management for search results."""

import json
from datetime import datetime
from pathlib import Path
from threading import Lock


DATA_DIR = Path("data")
RESULTS_FILE = DATA_DIR / "results.json"
_file_lock = Lock()  # Thread-safe file access


def init_storage():
    """Initialize storage directories."""
    DATA_DIR.mkdir(exist_ok=True)
    if not RESULTS_FILE.exists():
        RESULTS_FILE.write_text(json.dumps({"results": [], "updated": None}))


def load_results() -> dict:
    """Load all search results."""
    init_storage()
    with _file_lock:
        try:
            return json.loads(RESULTS_FILE.read_text())
        except json.JSONDecodeError:
            # If corrupted, reset
            RESULTS_FILE.write_text(json.dumps({"results": [], "updated": None}))
            return json.loads(RESULTS_FILE.read_text())


def save_result(gpu_name: str, listing_data: dict):
    """Save a single search result (thread-safe)."""
    init_storage()
    
    with _file_lock:
        try:
            data = json.loads(RESULTS_FILE.read_text())
        except json.JSONDecodeError:
            # If results.json is corrupted, reset it
            data = {"results": [], "updated": None}
        
        result_entry = {
            "gpu_name": gpu_name,
            "title": listing_data.get("title"),
            "price": listing_data.get("price"),
            "link": listing_data.get("link"),
            "date": listing_data.get("date"),
            "location": listing_data.get("location"),
            "timestamp": datetime.now().isoformat(),
        }
        
        # Avoid duplicates by checking title+price+date
        key = f"{gpu_name}_{listing_data.get('title')}_{listing_data.get('price')}"
        existing = data["results"]
        
        # Remove old entries with same key
        data["results"] = [
            r for r in existing 
            if f"{r['gpu_name']}_{r['title']}_{r['price']}" != key
        ]
        
        data["results"].append(result_entry)
        data["updated"] = datetime.now().isoformat()
        
        RESULTS_FILE.write_text(json.dumps(data, indent=2))


def get_results_by_gpu(gpu_name: str) -> list[dict]:
    """Get all results for a specific GPU."""
    data = load_results()
    return [r for r in data["results"] if r["gpu_name"] == gpu_name]


def get_price_history(gpu_name: str) -> list[tuple]:
    """Get price history for a GPU (timestamp, avg_price)."""
    results = get_results_by_gpu(gpu_name)
    
    # Group by day and calculate average price
    price_by_date = {}
    for r in results:
        date = r["timestamp"][:10]  # YYYY-MM-DD
        price = r.get("price", 0)
        
        if not isinstance(price, (int, float)):
            continue
            
        if date not in price_by_date:
            price_by_date[date] = []
        price_by_date[date].append(price)
    
    # Calculate averages
    history = [
        (date, sum(prices) / len(prices))
        for date, prices in sorted(price_by_date.items())
    ]
    return history


def get_latest_listings() -> list[dict]:
    """Get latest listings for each GPU."""
    data = load_results()
    
    # Keep only latest for each GPU
    latest = {}
    for r in reversed(data["results"]):
        gpu = r["gpu_name"]
        if gpu not in latest:
            latest[gpu] = r
    
    return list(latest.values())
