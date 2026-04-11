from datetime import datetime, timezone

from zoneinfo import ZoneInfo

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def get_shanghai_now() -> datetime:
    # DB columns are DateTime (without timezone). Store a naive Shanghai timestamp
    # to avoid driver-side timezone conversion drift.
    return datetime.now(SHANGHAI_TZ).replace(tzinfo=None)


def get_shanghai_utc_now() -> datetime:
    return datetime.now(SHANGHAI_TZ).astimezone(timezone.utc)


def format_shanghai_dt(dt: datetime | None = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if dt is None:
        dt = get_shanghai_now()
    return dt.strftime(fmt)


def parse_shanghai_dt(dt_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    return datetime.strptime(dt_str, fmt).replace(tzinfo=SHANGHAI_TZ)


def to_shanghai_iso(dt: datetime | None) -> str | None:
    """Serialize datetime consistently in Asia/Shanghai ISO 8601 format."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Current project stores naive datetimes; interpret them as Asia/Shanghai.
        dt = dt.replace(tzinfo=SHANGHAI_TZ)
    else:
        dt = dt.astimezone(SHANGHAI_TZ)
    return dt.isoformat()