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


def calc_price_history(results: list[dict]) -> list[tuple]:
    """Calculate daily average prices (date, price)."""
    prices_by_date = {}
    
    for r in results:
        try:
            ts = datetime.fromisoformat(r.get("timestamp", ""))
            date = ts.date()
            price = r.get("price")
            
            if not isinstance(price, (int, float)):
                continue
                
            if date not in prices_by_date:
                prices_by_date[date] = []
            prices_by_date[date].append(price)
        except (ValueError, TypeError):
            continue
    
    history = [
        (str(date), mean(prices))
        for date, prices in sorted(prices_by_date.items())
    ]
    
    return history
