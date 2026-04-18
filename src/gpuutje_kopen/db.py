"""SQLite database layer – single source of truth for GPUs and listings."""

import json
import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean
from threading import local

log = logging.getLogger(__name__)

DB_PATH = Path("data/gpuutje.db")

_local = local()


def _conn() -> sqlite3.Connection:
    """Return a thread-local connection with WAL mode."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return conn


def init_db():
    """Create tables if they don't exist."""
    c = _conn()

    c.execute("""CREATE TABLE IF NOT EXISTS gpus (
        id            TEXT PRIMARY KEY,
        name          TEXT NOT NULL UNIQUE,
        tokens_sec    REAL NOT NULL DEFAULT 0,
        vram          INTEGER NOT NULL DEFAULT 0,
        search_queries TEXT NOT NULL DEFAULT '[]',
        tokens_tested INTEGER NOT NULL DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS listings (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        gpu_id      TEXT NOT NULL REFERENCES gpus(id) ON DELETE CASCADE,
        listing_id  TEXT,
        title       TEXT NOT NULL,
        price       REAL,
        link        TEXT,
        date        TEXT,
        location    TEXT,
        timestamp   TEXT NOT NULL,
        active      INTEGER NOT NULL DEFAULT 1,
        user_restored INTEGER NOT NULL DEFAULT 0
    )""")

    c.execute("CREATE INDEX IF NOT EXISTS idx_listings_gpu    ON listings(gpu_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_listings_active ON listings(gpu_id, active)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_listings_dedup ON listings(gpu_id, title, price)")

    c.execute("""CREATE TABLE IF NOT EXISTS outliers (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        gpu_id      TEXT NOT NULL,
        listing_id  TEXT,
        title       TEXT NOT NULL,
        price       REAL,
        link        TEXT,
        date        TEXT,
        location    TEXT,
        timestamp   TEXT NOT NULL,
        active      INTEGER NOT NULL DEFAULT 0,
        reason      TEXT,
        moved_at    TEXT NOT NULL
    )""")

    c.execute("CREATE INDEX IF NOT EXISTS idx_outliers_gpu ON outliers(gpu_id)")

    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""")

    c.commit()

    # Seed default settings
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('search_interval', '300')")
    c.commit()

    # Migration: add user_restored column if missing
    cols = {r[1] for r in c.execute("PRAGMA table_info(listings)").fetchall()}
    if "user_restored" not in cols:
        c.execute("ALTER TABLE listings ADD COLUMN user_restored INTEGER NOT NULL DEFAULT 0")
        c.commit()

    # Dedup outliers before creating unique index (handles pre-existing dupes)
    c.execute("""DELETE FROM outliers WHERE id NOT IN (
        SELECT MAX(id) FROM outliers GROUP BY gpu_id, title, price
    )""")
    c.commit()

    c.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_outliers_dedup
        ON outliers(gpu_id, title, price)""")
    c.commit()


# ── Settings helpers ──────────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    row = _conn().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    _conn().execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    _conn().commit()


# ── GPU dataclass ─────────────────────────────────────────────────────

@dataclass
class GPU:
    id: str
    name: str
    tokens_sec: float
    vram: int
    search_queries: list[str]
    tokens_tested: bool = False


def _row_to_gpu(row: sqlite3.Row) -> GPU:
    return GPU(
        id=row["id"],
        name=row["name"],
        tokens_sec=row["tokens_sec"],
        vram=row["vram"],
        search_queries=json.loads(row["search_queries"]),
        tokens_tested=bool(row["tokens_tested"]),
    )


# ── GPU CRUD ──────────────────────────────────────────────────────────

def load_gpu_list() -> list[GPU]:
    rows = _conn().execute("SELECT * FROM gpus ORDER BY id").fetchall()
    return [_row_to_gpu(r) for r in rows]


def get_gpu(gpu_id: str) -> GPU | None:
    row = _conn().execute("SELECT * FROM gpus WHERE id=?", (gpu_id,)).fetchone()
    return _row_to_gpu(row) if row else None


def add_gpu(gpu: GPU):
    _conn().execute(
        "INSERT INTO gpus (id,name,tokens_sec,vram,search_queries,tokens_tested) VALUES (?,?,?,?,?,?)",
        (gpu.id, gpu.name, gpu.tokens_sec, gpu.vram,
         json.dumps(gpu.search_queries), int(gpu.tokens_tested)),
    )
    _conn().commit()


def update_gpu(gpu_id: str, fields: dict) -> GPU:
    gpu = get_gpu(gpu_id)
    if not gpu:
        raise ValueError(f"GPU '{gpu_id}' not found")

    name = fields.get("name", gpu.name)
    tokens_sec = float(fields.get("tokens_sec", gpu.tokens_sec))
    vram = int(fields.get("vram", gpu.vram))
    sq = fields.get("search_queries", gpu.search_queries)
    tested = bool(fields.get("tokens_tested", gpu.tokens_tested))

    _conn().execute(
        "UPDATE gpus SET name=?,tokens_sec=?,vram=?,search_queries=?,tokens_tested=? WHERE id=?",
        (name, tokens_sec, vram, json.dumps(sq), int(tested), gpu_id),
    )
    _conn().commit()
    return get_gpu(gpu_id)


def delete_gpu(gpu_id: str):
    cur = _conn().execute("DELETE FROM gpus WHERE id=?", (gpu_id,))
    _conn().commit()
    if cur.rowcount == 0:
        raise ValueError(f"GPU '{gpu_id}' not found")


def next_gpu_id(name: str) -> str:
    """Generate a slug-style ID for a new GPU."""
    base = name.lower().replace(" ", "-")
    existing = {r["id"] for r in _conn().execute("SELECT id FROM gpus").fetchall()}
    if base not in existing:
        return base
    i = 2
    while f"{base}-{i}" in existing:
        i += 1
    return f"{base}-{i}"


# ── Listing CRUD ──────────────────────────────────────────────────────

def save_listing(gpu_id: str, data: dict):
    """Insert or replace a listing (dedup on gpu_id+title+price)."""
    _conn().execute("""
        INSERT INTO listings (gpu_id, listing_id, title, price, link, date, location, timestamp, active)
        VALUES (?,?,?,?,?,?,?,?,1)
        ON CONFLICT(gpu_id, title, price) DO UPDATE SET
            listing_id=excluded.listing_id,
            link=excluded.link,
            date=excluded.date,
            location=excluded.location,
            timestamp=excluded.timestamp,
            active=1
    """, (
        gpu_id,
        data.get("id"),
        data.get("title"),
        data.get("price"),
        data.get("link"),
        data.get("date"),
        data.get("location"),
        datetime.now().isoformat(),
    ))
    _conn().commit()


def mark_active_listings(gpu_id: str, active_listing_ids: set[str]):
    """Set active=1 for ids in the set, active=0 for others."""
    c = _conn()
    c.execute("UPDATE listings SET active=0 WHERE gpu_id=? AND listing_id IS NOT NULL", (gpu_id,))
    if active_listing_ids:
        placeholders = ",".join("?" * len(active_listing_ids))
        c.execute(
            f"UPDATE listings SET active=1 WHERE gpu_id=? AND listing_id IN ({placeholders})",
            (gpu_id, *active_listing_ids),
        )
    c.commit()


def update_listing(listing_pk: int, fields: dict) -> dict | None:
    """Update a listing by its primary key."""
    row = _conn().execute("SELECT * FROM listings WHERE id=?", (listing_pk,)).fetchone()
    if not row:
        return None
    allowed = {"title", "price", "active", "link", "gpu_id"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if "active" in updates:
        updates["active"] = int(updates["active"])
    if not updates:
        return dict(row)
    set_clause = ", ".join(f"{k}=?" for k in updates)
    _conn().execute(f"UPDATE listings SET {set_clause} WHERE id=?", (*updates.values(), listing_pk))
    _conn().commit()
    return dict(_conn().execute("SELECT * FROM listings WHERE id=?", (listing_pk,)).fetchone())


def delete_listing(listing_pk: int) -> bool:
    cur = _conn().execute("DELETE FROM listings WHERE id=?", (listing_pk,))
    _conn().commit()
    return cur.rowcount > 0


def delete_listings_by_gpu(gpu_id: str) -> int:
    cur = _conn().execute("DELETE FROM listings WHERE gpu_id=?", (gpu_id,))
    _conn().commit()
    return cur.rowcount


# ── Queries (push work into SQL) ──────────────────────────────────────

def listing_count() -> int:
    return _conn().execute("SELECT COUNT(*) FROM listings").fetchone()[0]


def active_listing_count() -> int:
    return _conn().execute("SELECT COUNT(*) FROM listings WHERE active=1").fetchone()[0]


def gpu_listing_counts() -> dict[str, int]:
    """Return {gpu_id: count} for all GPUs."""
    rows = _conn().execute("SELECT gpu_id, COUNT(*) AS cnt FROM listings GROUP BY gpu_id").fetchall()
    return {r["gpu_id"]: r["cnt"] for r in rows}


def last_updated() -> str | None:
    row = _conn().execute("SELECT MAX(timestamp) AS ts FROM listings").fetchone()
    return row["ts"] if row else None


def gpu_breakdown() -> list[dict]:
    """One query to get breakdown stats per GPU."""
    rows = _conn().execute("""
        SELECT
            g.id, g.name, g.vram, g.tokens_sec,
            COUNT(l.id)                           AS total,
            SUM(CASE WHEN l.active=1 THEN 1 ELSE 0 END) AS active,
            MIN(l.price)                          AS min_price,
            MAX(l.price)                          AS max_price
        FROM gpus g
        LEFT JOIN listings l ON l.gpu_id = g.id
        GROUP BY g.id
        ORDER BY g.id
    """).fetchall()
    return [dict(r) for r in rows]


def price_history(gpu_id: str, agg: str = "min", span: str = "30d") -> list[tuple[str, float]]:
    """Return (date, price) pairs, binned by day or week."""
    cutoff, bin_expr = _span_to_sql(span)
    agg_fn = "MIN" if agg == "min" else "AVG"
    rows = _conn().execute(f"""
        SELECT {bin_expr} AS period, {agg_fn}(price) AS val
        FROM listings
        WHERE gpu_id=? AND price IS NOT NULL AND date >= ?
        GROUP BY period ORDER BY period
    """, (gpu_id, cutoff)).fetchall()
    return [(r["period"], r["val"]) for r in rows]


def avg_price_period(gpu_id: str, days: int | None) -> float:
    """Average price for a GPU over given days (None=all time)."""
    if days is None:
        row = _conn().execute(
            "SELECT AVG(price) AS a FROM listings WHERE gpu_id=? AND price IS NOT NULL",
            (gpu_id,),
        ).fetchone()
    else:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        row = _conn().execute(
            "SELECT AVG(price) AS a FROM listings WHERE gpu_id=? AND price IS NOT NULL AND date>=?",
            (gpu_id, cutoff),
        ).fetchone()
    return row["a"] or 0


def lowest_listing(gpu_id: str) -> dict | None:
    """Cheapest listing (prefer active)."""
    row = _conn().execute("""
        SELECT price, link, title, timestamp, active
        FROM listings WHERE gpu_id=? AND price IS NOT NULL
        ORDER BY active DESC, price ASC LIMIT 1
    """, (gpu_id,)).fetchone()
    return dict(row) if row else None


def filtered_listings(
    *,
    gpu_ids: list[str] | None = None,
    min_price: float = 0,
    max_price: float = 999999,
    search: str = "",
    active_only: bool = False,
    sort_by: str = "timestamp",
    order: str = "desc",
    limit: int = 500,
) -> list[dict]:
    """Filtered listing query with GPU enrichment."""
    conditions = ["l.price IS NOT NULL", "l.price >= ?", "l.price <= ?"]
    params: list = [min_price, max_price]

    if gpu_ids:
        placeholders = ",".join("?" * len(gpu_ids))
        conditions.append(f"l.gpu_id IN ({placeholders})")
        params.extend(gpu_ids)
    if search:
        conditions.append("l.title LIKE ?")
        params.append(f"%{search}%")
    if active_only:
        conditions.append("l.active=1")

    sort_col = {
        "price": "l.price",
        "gpu": "g.name",
        "vram": "g.vram",
        "tokens": "g.tokens_sec",
    }.get(sort_by, "l.timestamp")
    direction = "ASC" if order == "asc" else "DESC"

    sql = f"""
        SELECT l.*, g.name AS gpu_name, g.vram, g.tokens_sec, g.tokens_tested
        FROM listings l
        JOIN gpus g ON g.id = l.gpu_id
        WHERE {' AND '.join(conditions)}
        ORDER BY {sort_col} {direction}
        LIMIT ?
    """
    params.append(limit)
    rows = _conn().execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def browse_listings(
    *,
    gpu_filter: str = "",
    search: str = "",
    min_price: float = 0,
    max_price: float = 999999,
    active_only: bool = False,
    sort_by: str = "timestamp",
    order: str = "desc",
    limit: int = 200,
) -> list[dict]:
    """Admin browse with full filtering – single SQL query."""
    conditions = ["l.price IS NOT NULL", "l.price >= ?", "l.price <= ?"]
    params: list = [min_price, max_price]

    if gpu_filter:
        conditions.append("(LOWER(g.name) LIKE ? OR LOWER(g.id) LIKE ?)")
        patt = f"%{gpu_filter.lower()}%"
        params.extend([patt, patt])
    if search:
        conditions.append("LOWER(l.title) LIKE ?")
        params.append(f"%{search.lower()}%")
    if active_only:
        conditions.append("l.active=1")

    sort_col = {
        "price": "l.price",
        "gpu": "g.name",
        "vram": "g.vram",
        "tokens": "g.tokens_sec",
    }.get(sort_by, "l.timestamp")
    direction = "ASC" if order == "asc" else "DESC"

    sql = f"""
        SELECT l.id, l.gpu_id, g.name AS gpu_name, l.listing_id, l.title,
               l.price, l.link, l.date, l.location, l.timestamp, l.active,
               g.vram, g.tokens_sec
        FROM listings l
        JOIN gpus g ON g.id = l.gpu_id
        WHERE {' AND '.join(conditions)}
        ORDER BY {sort_col} {direction}
        LIMIT ?
    """
    params.append(limit)
    return [dict(r) for r in _conn().execute(sql, params).fetchall()]


# ── Helpers ───────────────────────────────────────────────────────────

def _span_to_sql(span: str) -> tuple[str, str]:
    """Return (cutoff_date_str, sql_bin_expression)."""
    now = datetime.now()
    try:
        if span.endswith("d"):
            days = int(span[:-1])
        elif span.endswith("y"):
            days = int(span[:-1]) * 365
        else:
            days = 30
    except (ValueError, AttributeError):
        days = 30

    cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    # For spans ≤60 days bin by day, otherwise by ISO week start (Monday)
    if days <= 60:
        bin_expr = "SUBSTR(date,1,10)"
    else:
        bin_expr = "DATE(date, 'weekday 1', '-7 days')"
    return cutoff, bin_expr


# ── Outlier detection ─────────────────────────────────────────────────

OUTLIER_THRESHOLD_BELOW = 0.50  # flag if price < 50% of mean
OUTLIER_THRESHOLD_ABOVE = 1.00  # flag if price > 100% above mean
OUTLIER_MIN_LISTINGS = 5  # need at least this many listings to judge


def _is_outlier_price(price: float, mean_p: float) -> tuple[bool, str]:
    """Check asymmetric outlier thresholds. Returns (is_outlier, reason)."""
    if mean_p <= 0:
        return False, ""
    if price < mean_p * (1 - OUTLIER_THRESHOLD_BELOW):
        pct = (mean_p - price) / mean_p
        return True, f"price €{price:.0f} is {pct:.0%} below mean €{mean_p:.0f}"
    if price > mean_p * (1 + OUTLIER_THRESHOLD_ABOVE):
        pct = (price - mean_p) / mean_p
        return True, f"price €{price:.0f} is {pct:.0%} above mean €{mean_p:.0f}"
    return False, ""


def _gpu_mean_prices() -> dict[str, tuple[float, int]]:
    """Return {gpu_id: (mean_price, count)} for GPUs with enough listings."""
    rows = _conn().execute("""
        SELECT gpu_id, AVG(price) AS avg_p, COUNT(*) AS cnt
        FROM listings WHERE price IS NOT NULL
        GROUP BY gpu_id HAVING cnt >= ?
    """, (OUTLIER_MIN_LISTINGS,)).fetchall()
    return {r["gpu_id"]: (r["avg_p"], r["cnt"]) for r in rows}


def is_price_outlier(gpu_id: str, price: float) -> tuple[bool, str]:
    """Check if a price is >50% below or >100% above the GPU's mean.
    Returns (is_outlier, reason_string)."""
    row = _conn().execute(
        "SELECT AVG(price) AS avg_p, COUNT(*) AS cnt FROM listings WHERE gpu_id=? AND price IS NOT NULL",
        (gpu_id,),
    ).fetchone()
    if not row or row["cnt"] < OUTLIER_MIN_LISTINGS:
        return False, ""
    return _is_outlier_price(price, row["avg_p"])


def _move_listing_to_outliers(listing_pk: int, reason: str):
    """Move a listing row into the outliers table and delete from listings."""
    c = _conn()
    row = c.execute("SELECT * FROM listings WHERE id=?", (listing_pk,)).fetchone()
    if not row:
        return
    c.execute("""
        INSERT INTO outliers (gpu_id, listing_id, title, price, link, date, location, timestamp, active, reason, moved_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(gpu_id, title, price) DO UPDATE SET
            listing_id=excluded.listing_id, link=excluded.link,
            reason=excluded.reason, moved_at=excluded.moved_at
    """, (
        row["gpu_id"], row["listing_id"], row["title"], row["price"],
        row["link"], row["date"], row["location"], row["timestamp"],
        row["active"], reason, datetime.now().isoformat(),
    ))
    c.execute("DELETE FROM listings WHERE id=?", (listing_pk,))
    c.commit()


def save_as_outlier(gpu_id: str, data: dict, reason: str):
    """Save a new listing directly as an outlier (dedup on gpu_id+title+price)."""
    _conn().execute("""
        INSERT INTO outliers (gpu_id, listing_id, title, price, link, date, location, timestamp, active, reason, moved_at)
        VALUES (?,?,?,?,?,?,?,?,0,?,?)
        ON CONFLICT(gpu_id, title, price) DO UPDATE SET
            listing_id=excluded.listing_id, link=excluded.link,
            reason=excluded.reason, moved_at=excluded.moved_at
    """, (
        gpu_id, data.get("id"), data.get("title"), data.get("price"),
        data.get("link"), data.get("date"), data.get("location"),
        datetime.now().isoformat(), reason, datetime.now().isoformat(),
    ))
    _conn().commit()


def sweep_outliers() -> dict[str, int]:
    """Scan listings→outliers and outliers→listings. Returns {"moved": n, "restored": n}."""
    means = _gpu_mean_prices()
    moved = 0
    for gpu_id, (mean_p, _cnt) in means.items():
        if mean_p <= 0:
            continue
        rows = _conn().execute(
            "SELECT id, price FROM listings WHERE gpu_id=? AND price IS NOT NULL AND user_restored=0",
            (gpu_id,),
        ).fetchall()
        for r in rows:
            is_outlier, reason = _is_outlier_price(r["price"], mean_p)
            if is_outlier:
                _move_listing_to_outliers(r["id"], reason)
                moved += 1

    # Reverse: restore outliers that are no longer outliers
    restored = 0
    # Recompute means after moving
    means = _gpu_mean_prices()
    outlier_rows = _conn().execute(
        "SELECT id, gpu_id, price FROM outliers WHERE price IS NOT NULL"
    ).fetchall()
    for o in outlier_rows:
        stats = means.get(o["gpu_id"])
        if not stats:
            continue
        mean_p, _ = stats
        if mean_p <= 0:
            continue
        is_outlier, _ = _is_outlier_price(o["price"], mean_p)
        if not is_outlier:
            restore_outlier(o["id"])
            restored += 1

    return {"moved": moved, "restored": restored}


def dedup_tables() -> dict[str, int]:
    """Remove duplicate rows from listings and outliers.

    Duplicates are identified by:
      1. Same listing_id (marktplaats id) within the same table
      2. Same link URL within the same table
    Keeps the row with the highest primary key (most recent insert).
    Returns {"listings": n, "outliers": n} with counts of removed dupes.
    """
    c = _conn()
    removed = {"listings": 0, "outliers": 0}

    for table in ("listings", "outliers"):
        # Dedup by listing_id (keep highest pk)
        cur = c.execute(f"""
            DELETE FROM {table} WHERE id NOT IN (
                SELECT MAX(id) FROM {table}
                WHERE listing_id IS NOT NULL
                GROUP BY listing_id
            ) AND listing_id IS NOT NULL
            AND listing_id IN (
                SELECT listing_id FROM {table}
                WHERE listing_id IS NOT NULL
                GROUP BY listing_id HAVING COUNT(*) > 1
            )
        """)
        removed[table] += cur.rowcount

        # Dedup by link URL (keep highest pk)
        cur = c.execute(f"""
            DELETE FROM {table} WHERE id NOT IN (
                SELECT MAX(id) FROM {table}
                WHERE link IS NOT NULL AND link != ''
                GROUP BY link
            ) AND link IS NOT NULL AND link != ''
            AND link IN (
                SELECT link FROM {table}
                WHERE link IS NOT NULL AND link != ''
                GROUP BY link HAVING COUNT(*) > 1
            )
        """)
        removed[table] += cur.rowcount

    c.commit()
    return removed


def outlier_count() -> int:
    return _conn().execute("SELECT COUNT(*) FROM outliers").fetchone()[0]


def browse_outliers(
    *,
    gpu_filter: str = "",
    sort_by: str = "moved_at",
    order: str = "desc",
    limit: int = 200,
) -> list[dict]:
    """Browse outliers with optional GPU filter."""
    conditions = ["1=1"]
    params: list = []
    if gpu_filter:
        conditions.append("(LOWER(g.name) LIKE ? OR LOWER(o.gpu_id) LIKE ?)")
        patt = f"%{gpu_filter.lower()}%"
        params.extend([patt, patt])

    sort_col = {
        "price": "o.price",
        "gpu": "g.name",
        "moved_at": "o.moved_at",
    }.get(sort_by, "o.moved_at")
    direction = "ASC" if order == "asc" else "DESC"

    sql = f"""
        SELECT o.id, o.gpu_id, COALESCE(g.name, o.gpu_id) AS gpu_name,
               o.title, o.price, o.link, o.date, o.timestamp,
               o.reason, o.moved_at
        FROM outliers o
        LEFT JOIN gpus g ON g.id = o.gpu_id
        WHERE {' AND '.join(conditions)}
        ORDER BY {sort_col} {direction}
        LIMIT ?
    """
    params.append(limit)
    return [dict(r) for r in _conn().execute(sql, params).fetchall()]


def restore_outlier(outlier_pk: int) -> bool:
    """Move an outlier back into the listings table."""
    c = _conn()
    row = c.execute("SELECT * FROM outliers WHERE id=?", (outlier_pk,)).fetchone()
    if not row:
        return False
    try:
        c.execute("""
            INSERT INTO listings (gpu_id, listing_id, title, price, link, date, location, timestamp, active, user_restored)
            VALUES (?,?,?,?,?,?,?,?,?,1)
            ON CONFLICT(gpu_id, title, price) DO UPDATE SET
                listing_id=excluded.listing_id, link=excluded.link,
                timestamp=excluded.timestamp, user_restored=1
        """, (
            row["gpu_id"], row["listing_id"], row["title"], row["price"],
            row["link"], row["date"], row["location"], row["timestamp"], 0,
        ))
        c.execute("DELETE FROM outliers WHERE id=?", (outlier_pk,))
        c.commit()
        return True
    except Exception as e:
        log.error(f"restore_outlier({outlier_pk}) failed: {e}")
        return False


def delete_outlier(outlier_pk: int) -> bool:
    cur = _conn().execute("DELETE FROM outliers WHERE id=?", (outlier_pk,))
    _conn().commit()
    return cur.rowcount > 0


def browse_restored_listings(
    *,
    gpu_filter: str = "",
    limit: int = 200,
) -> list[dict]:
    """Browse listings that were manually restored from outliers."""
    conditions = ["l.user_restored = 1"]
    params: list = []
    if gpu_filter:
        conditions.append("(LOWER(g.name) LIKE ? OR LOWER(l.gpu_id) LIKE ?)")
        patt = f"%{gpu_filter.lower()}%"
        params.extend([patt, patt])

    sql = f"""
        SELECT l.id, l.gpu_id, COALESCE(g.name, l.gpu_id) AS gpu_name,
               l.title, l.price, l.link, l.date, l.timestamp
        FROM listings l
        LEFT JOIN gpus g ON g.id = l.gpu_id
        WHERE {' AND '.join(conditions)}
        ORDER BY l.timestamp DESC
        LIMIT ?
    """
    params.append(limit)
    return [dict(r) for r in _conn().execute(sql, params).fetchall()]


def unrestore_listing(listing_pk: int) -> bool:
    """Move a user-restored listing back to outliers. Undoes a manual restore."""
    c = _conn()
    row = c.execute(
        "SELECT * FROM listings WHERE id=? AND user_restored=1", (listing_pk,)
    ).fetchone()
    if not row:
        return False
    try:
        reason = "manually re-flagged by admin"
        c.execute("""
            INSERT INTO outliers (gpu_id, listing_id, title, price, link, date, location, timestamp, active, reason, moved_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(gpu_id, title, price) DO UPDATE SET
                listing_id=excluded.listing_id, link=excluded.link,
                reason=excluded.reason, moved_at=excluded.moved_at
        """, (
            row["gpu_id"], row["listing_id"], row["title"], row["price"],
            row["link"], row["date"], row["location"], row["timestamp"],
            0, reason, datetime.now().isoformat(),
        ))
        c.execute("DELETE FROM listings WHERE id=?", (listing_pk,))
        c.commit()
        return True
    except Exception as e:
        log.error(f"unrestore_listing({listing_pk}) failed: {e}")
        return False


def revalidate_listings() -> dict:
    """Re-validate all listings against current validation algorithm.

    Returns dict with counts: deleted, corrected, unchanged.
    """
    from .validation import find_best_gpu_match

    rows = _conn().execute(
        "SELECT id, gpu_id, title FROM listings"
    ).fetchall()

    stats = {"deleted": 0, "corrected": 0, "unchanged": 0}
    c = _conn()

    for row in rows:
        pk, stored_gpu_id, title = row["id"], row["gpu_id"], row["title"]
        best_gpu_id, word_count = find_best_gpu_match(title)

        if best_gpu_id is None or word_count == 0:
            c.execute("DELETE FROM listings WHERE id=?", (pk,))
            stats["deleted"] += 1
        elif best_gpu_id != stored_gpu_id:
            try:
                c.execute(
                    "UPDATE listings SET gpu_id=? WHERE id=?",
                    (best_gpu_id, pk),
                )
                stats["corrected"] += 1
            except sqlite3.IntegrityError:
                # Corrected gpu_id creates a duplicate — remove this row
                c.execute("DELETE FROM listings WHERE id=?", (pk,))
                stats["deleted"] += 1
        else:
            stats["unchanged"] += 1

        # Commit in small batches to avoid holding the write lock too long
        total = stats["deleted"] + stats["corrected"] + stats["unchanged"]
        if total % 50 == 0:
            c.commit()

    c.commit()
    return stats


def revalidate_outliers() -> dict:
    """Re-validate all outliers against current validation algorithm.

    Deletes outliers that no longer match any GPU, corrects gpu_id for
    mismatched ones.  Returns dict with counts: deleted, corrected, unchanged.
    """
    from .validation import find_best_gpu_match

    rows = _conn().execute(
        "SELECT id, gpu_id, title FROM outliers"
    ).fetchall()

    stats = {"deleted": 0, "corrected": 0, "unchanged": 0}
    c = _conn()

    for row in rows:
        pk, stored_gpu_id, title = row["id"], row["gpu_id"], row["title"]
        best_gpu_id, word_count = find_best_gpu_match(title)

        if best_gpu_id is None or word_count == 0:
            c.execute("DELETE FROM outliers WHERE id=?", (pk,))
            stats["deleted"] += 1
        elif best_gpu_id != stored_gpu_id:
            try:
                c.execute(
                    "UPDATE outliers SET gpu_id=? WHERE id=?",
                    (best_gpu_id, pk),
                )
                stats["corrected"] += 1
            except sqlite3.IntegrityError:
                c.execute("DELETE FROM outliers WHERE id=?", (pk,))
                stats["deleted"] += 1
        else:
            stats["unchanged"] += 1

        total = stats["deleted"] + stats["corrected"] + stats["unchanged"]
        if total % 50 == 0:
            c.commit()

    c.commit()
    return stats
