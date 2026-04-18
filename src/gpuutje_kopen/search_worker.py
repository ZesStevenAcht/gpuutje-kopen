"""Periodic GPU search worker."""

import logging
import time
from threading import Thread, Event

from marktplaats import SearchQuery, category_from_name

from .db import GPU, load_gpu_list, save_listing, mark_active_listings, get_gpu, is_price_outlier, save_as_outlier, sweep_outliers, dedup_tables, revalidate_listings, revalidate_outliers, get_setting, set_setting, _conn
from .validation import validate_listing, reload_gpu_cache

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

SEARCH_INTERVAL = 300  # default fallback


def get_search_interval() -> int:
    try:
        return int(get_setting("search_interval", str(SEARCH_INTERVAL)))
    except (ValueError, TypeError):
        return SEARCH_INTERVAL


def set_search_interval(seconds: int):
    seconds = max(60, min(seconds, 3600))  # clamp 1min–1hr
    set_setting("search_interval", str(seconds))


def search_gpu(gpu: GPU, gpu_by_id: dict[str, GPU]) -> int:
    """Search for a GPU and save results. Returns count of saved listings."""
    found = 0
    found_ids: set[str] = set()

    for query_str in gpu.search_queries:
        try:
            listings = SearchQuery(
                query=query_str,
                zip_code="1016LV",
                distance=100000000,
                limit=100,
                category=category_from_name("Videokaarten"),
            ).get_listings()

            for listing in listings:
                try:
                    title = str(getattr(listing, "title", "Unknown") or "Unknown")
                    price = getattr(listing, "price", None)
                    if price is not None:
                        try:
                            price = float(price)
                        except (ValueError, TypeError):
                            continue
                    if price is None or price < 150:
                        continue

                    link = getattr(listing, "link", "")
                    date = getattr(listing, "date", None)
                    listing_id = getattr(listing, "id", None)
                    location = getattr(listing, "location", None)
                    location_str = None
                    if location:
                        try:
                            location_str = getattr(location, "city", None)
                        except Exception:
                            pass

                    is_valid, corrected_id, score = validate_listing(gpu.id, title)
                    if not is_valid:
                        continue

                    target_id = corrected_id or gpu.id
                    if corrected_id:
                        target = gpu_by_id.get(target_id)
                        log.info(f"Corrected: '{title[:50]}' -> {target.name if target else target_id}")

                    listing_data = {
                        "id": str(listing_id) if listing_id is not None else None,
                        "title": title,
                        "price": price,
                        "link": link,
                        "date": date.isoformat() if date else None,
                        "location": location_str,
                    }

                    # Check price outlier before saving
                    outlier, reason = is_price_outlier(target_id, price)
                    if outlier:
                        save_as_outlier(target_id, listing_data, reason)
                        log.info(f"Outlier: '{title[:50]}' ({reason})")
                        continue

                    save_listing(target_id, listing_data)
                    if listing_id is not None:
                        found_ids.add(str(listing_id))
                    found += 1
                except Exception as e:
                    log.debug(f"Error processing listing: {e}")

        except Exception as e:
            log.error(f"Error searching '{query_str}' for {gpu.name}: {e}")

    if found_ids:
        try:
            mark_active_listings(gpu.id, found_ids)
        except Exception as e:
            log.debug(f"Error marking active for {gpu.name}: {e}")

    return found


def run_search_cycle():
    """Run one complete search cycle through all GPUs."""
    log.info("Starting search cycle...")
    reload_gpu_cache()
    gpus = load_gpu_list()
    gpu_by_id = {g.id: g for g in gpus}
    total = 0
    for gpu in gpus:
        count = search_gpu(gpu, gpu_by_id)
        total += count
        log.info(f"Found {count} listings for {gpu.name}")
        time.sleep(0.5)

    # Re-validate listings against current matching algorithm
    rv = revalidate_listings()
    if rv["deleted"] or rv["corrected"]:
        log.info(f"Revalidation (listings): {rv['deleted']} deleted, {rv['corrected']} corrected")

    rv2 = revalidate_outliers()
    if rv2["deleted"] or rv2["corrected"]:
        log.info(f"Revalidation (outliers): {rv2['deleted']} deleted, {rv2['corrected']} corrected")

    # Sweep existing listings for outliers and restore false positives
    result = sweep_outliers()
    if result["moved"] or result["restored"]:
        log.info(f"Outlier sweep: {result['moved']} moved, {result['restored']} restored")

    # Deduplicate both tables by listing_id and link
    dupes = dedup_tables()
    if dupes["listings"] or dupes["outliers"]:
        log.info(f"Dedup: {dupes['listings']} listing dupes, {dupes['outliers']} outlier dupes removed")

    log.info(f"Search cycle complete. Total: {total}")


_stop_event = Event()


def worker_loop():
    log.info("Search worker started")
    while not _stop_event.is_set():
        try:
            run_search_cycle()
        except Exception as e:
            log.error(f"Search cycle error: {e}")
            try:
                _conn().rollback()
            except Exception:
                pass
        remaining = get_search_interval()
        while remaining > 0 and not _stop_event.is_set():
            time.sleep(min(1, remaining))
            remaining -= 1
    log.info("Search worker stopping")


def start_worker_thread() -> Thread:
    t = Thread(target=worker_loop, daemon=True)
    t.start()
    log.info("Search worker thread started")
    return t


def stop_worker_thread():
    _stop_event.set()
