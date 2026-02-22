"""Analytics for GPU data."""

from datetime import datetime, timedelta
from statistics import mean


def get_avg_price_period(results: list[dict], days: int | None) -> float:
    """Get average price over a period."""
    if not results:
        return 0
    
    if days is None:
        # All time
        prices = [r.get("price") for r in results if isinstance(r.get("price"), (int, float))]
    else:
        cutoff = datetime.now() - timedelta(days=days)
        prices = []
        for r in results:
            if not isinstance(r.get("price"), (int, float)):
                continue
            # Prefer listing 'date' if present, fallback to stored 'timestamp'
            date_str = r.get("date") or r.get("timestamp")
            try:
                dt = datetime.fromisoformat(date_str)
            except Exception:
                # skip entries with bad dates
                continue
            if dt > cutoff:
                prices.append(r.get("price"))
    
    return mean(prices) if prices else 0


def find_pareto_front(points: list[tuple]) -> list[tuple]:
    """Find Pareto front from (x, y) points."""
    if not points:
        return []
    
    # Sort by x ascending, y descending (we want high y, low x)
    sorted_pts = sorted(points, key=lambda p: (p[0], -p[1]))
    
    pareto = []
    max_y = -float("inf")
    
    for x, y in sorted_pts:
        if y > max_y:
            pareto.append((x, y))
            max_y = y
    
    return pareto


def calc_price_history(results: list[dict], agg: str = "min", span: str = "30d") -> list[tuple]:
    """Calculate price history for a time span.

    - `agg` can be 'min' or 'avg'.
    - `span` can be '14d', '30d', or '1y'.

    Returns a list of (period_start_iso_date, price) where period_start is per-day for short spans
    and per-week for yearly span.
    """
    groups: dict = {}
    now = datetime.now()

    # Determine cutoff and binning
    span = span or "30d"
    try:
        if span.endswith('d'):
            days = int(span[:-1])
            cutoff = now - timedelta(days=days)
            bin_by = 'day'
        elif span.endswith('y'):
            years = int(span[:-1])
            cutoff = now - timedelta(days=365 * years)
            bin_by = 'week'
        else:
            # fallback to 30 days
            days = 30
            cutoff = now - timedelta(days=days)
            bin_by = 'day'
    except Exception:
        cutoff = now - timedelta(days=30)
        bin_by = 'day'

    for r in results:
        try:
            date_str = r.get("date") or r.get("timestamp")
            ts = datetime.fromisoformat(date_str)
            price = r.get("price")

            if not isinstance(price, (int, float)):
                continue

            if ts < cutoff:
                continue

            if bin_by == 'day':
                key = ts.date().isoformat()
            else:
                # week: use ISO week start (Monday)
                start = ts - timedelta(days=ts.weekday())
                key = start.date().isoformat()

            groups.setdefault(key, []).append(price)
        except (ValueError, TypeError):
            continue

    history = []
    for key in sorted(groups.keys()):
        prices = groups[key]
        if not prices:
            continue

        if agg == "min":
            val = min(prices)
        else:
            val = mean(prices)

        history.append((str(key), val))

    return history
