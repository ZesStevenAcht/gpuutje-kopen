"""Periodic GPU search worker."""

import logging
import time
from datetime import datetime
from threading import Thread

from marktplaats import SearchQuery, category_from_name

from main import GPU_LIST
from storage import save_result
from validation import validate_listing


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

SEARCH_INTERVAL = 8 * 60 * 60  # 8 hours in seconds


def search_gpu(gpu: object) -> int:
    """Search for a GPU and save results."""
    found = 0
    
    for query_str in gpu.search_queries:
        try:
            search = SearchQuery(
                query=query_str,
                zip_code="1016LV",
                distance=100000000,
                limit=100,
                category=category_from_name("Videokaarten"),
            )
            listings = search.get_listings()
            
            for listing in listings:
                try:
                    # Safe extraction of listing data
                    title = getattr(listing, "title", "Unknown")
                    price = getattr(listing, "price", None)
                    link = getattr(listing, "link", "")
                    date = getattr(listing, "date", None)
                    location = getattr(listing, "location", None)
                    
                    # Ensure title is string
                    if not isinstance(title, str):
                        title = str(title) if title else "Unknown"
                    
                    # Ensure price is numeric
                    if price is not None:
                        try:
                            price = float(price)
                        except (ValueError, TypeError):
                            price = None
                    
                    # Skip listings with no price or extremely low price
                    if price is None:
                        continue
                    # Exclude listings below €50
                    if price < 50:
                        continue
                    
                    # Extract location city safely (avoid Python repr strings)
                    location_str = None
                    if location:
                        try:
                            # Try to get city from location object
                            city = getattr(location, "city", None)
                            location_str = city if city else None
                        except Exception:
                            location_str = None
                    
                    # Validate listing matches the correct GPU
                    is_valid, corrected_gpu, match_score = validate_listing(gpu.name, title)
                    
                    if not is_valid:
                        log.debug(f"Listing rejected (low match score): '{title[:50]}...' (score: {match_score:.1f})")
                        continue
                    
                    # Determine which GPU to save under
                    target_gpu = corrected_gpu if corrected_gpu else gpu.name
                    
                    # Log corrections
                    if corrected_gpu:
                        log.info(f"Listing corrected: '{title[:50]}...' -> {gpu.name} corrected to {corrected_gpu} (score: {match_score:.1f})")
                    
                    data = {
                        "title": title,
                        "price": price,
                        "link": link,
                        "date": date.isoformat() if date else None,
                        "location": location_str,
                    }
                    save_result(target_gpu, data)
                    found += 1
                except Exception as e:
                    log.debug(f"Error processing listing: {e}")
                    
        except Exception as e:
            log.error(f"Error searching '{query_str}' for {gpu.name}: {e}")
    
    return found


def run_search_cycle():
    """Run one complete search cycle through all GPUs."""
    log.info("Starting search cycle...")
    total = 0
    
    for gpu in GPU_LIST:
        count = search_gpu(gpu)
        total += count
        log.info(f"Found {count} listings for {gpu.name}")
        time.sleep(0.5)  # Be nice to the API
    
    log.info(f"Search cycle complete. Total results: {total}")


def worker_loop():
    """Run search loop indefinitely."""
    log.info("Search worker started")
    
    while True:
        try:
            run_search_cycle()
        except Exception as e:
            log.error(f"Unexpected error in search cycle: {e}")
        
        log.info(f"Next search in {SEARCH_INTERVAL / 3600:.0f} hours")
        time.sleep(SEARCH_INTERVAL)


def start_worker_thread():
    """Start search worker in a background thread."""
    thread = Thread(target=worker_loop, daemon=True)
    thread.start()
    log.info("Search worker thread started")
    return thread


if __name__ == "__main__":
    run_search_cycle()
