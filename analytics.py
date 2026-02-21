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
        prices = [
            r.get("price") for r in results
            if isinstance(r.get("price"), (int, float))
            and datetime.fromisoformat(r.get("timestamp", "")) > cutoff
        ]
    
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


def calc_price_history(results: list[dict], agg: str = "min", period: str = "day") -> list[tuple]:
    """Calculate price history aggregated by period.

    - `agg` can be 'min' or 'avg'.
    - `period` can be 'day', 'week', or 'month'.

    Returns list of (period_label, price).
    """
    groups: dict = {}

    for r in results:
        try:
            ts = datetime.fromisoformat(r.get("timestamp", ""))
            price = r.get("price")

            if not isinstance(price, (int, float)):
                continue

            if period == "day":
                key = ts.date()
            elif period == "week":
                iso = ts.isocalendar()
                key = f"{iso[0]}-W{iso[1]:02d}"  # e.g. 2026-W05
            elif period == "month":
                key = f"{ts.year}-{ts.month:02d}"
            else:
                key = ts.date()

            groups.setdefault(key, []).append(price)
        except (ValueError, TypeError):
            continue

    history = []
    # Sort keys chronologically when possible
    def sort_key(k):
        if isinstance(k, (str,)):
            # try ISO-like strings
            try:
                if "-W" in k:
                    yr, w = k.split("-W")
                    return (int(yr), int(w), 0)
                if "-" in k and len(k) == 7:
                    yr, m = k.split("-")
                    return (int(yr), int(m), 0)
            except Exception:
                return (k,)
        return (k,)

    for key in sorted(groups.keys(), key=sort_key):
        prices = groups[key]
        if not prices:
            continue

        if agg == "min":
            val = min(prices)
        else:
            val = mean(prices)

        history.append((str(key), val))

    return history
