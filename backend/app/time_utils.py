"""应用统一时间工具。"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """返回无时区 UTC 时间，兼容现有 SQLite DateTime 字段。"""
    return datetime.now(UTC).replace(tzinfo=None)
