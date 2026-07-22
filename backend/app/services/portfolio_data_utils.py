"""作品服务使用的纯数据清洗与安全校验工具。"""

import json
from urllib.parse import urlparse


def string_list(value) -> list[str]:
    """将列表成员转换为非空字符串。"""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def parse_string_list(value: str | None) -> list[str]:
    """解析数据库中的 JSON 字符串列表，异常内容返回空列表。"""
    if not value:
        return []
    try:
        return string_list(json.loads(value))
    except (json.JSONDecodeError, TypeError):
        return []


def record_list(value, fields: tuple[str, ...], limit: int) -> list[dict]:
    """按字段白名单和数量上限清洗记录列表。"""
    if not isinstance(value, list):
        return []
    records = []
    for raw in value[:limit]:
        if not isinstance(raw, dict):
            continue
        record = {}
        for field in fields:
            raw_value = raw.get(field)
            record[field] = (
                string_list(raw_value)
                if isinstance(raw_value, list)
                else str(raw_value or "").strip()
            )
        records.append(record)
    return records


def parse_record_list(value: str | None) -> list[dict]:
    """解析数据库中的 JSON 记录列表，过滤非对象成员。"""
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return (
            [item for item in parsed if isinstance(item, dict)]
            if isinstance(parsed, list)
            else []
        )
    except (json.JSONDecodeError, TypeError):
        return []


def parse_json_dict(value: str | None) -> dict:
    """解析数据库中的 JSON 对象，异常内容返回空对象。"""
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def strip_code_fence(value: str) -> str:
    """移除 AI 可能附加的 Markdown 代码围栏。"""
    stripped = value.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        return "\n".join(lines[1:-1]).strip()
    return stripped


def normalize_optional_url(value: str | None, field_name: str) -> str | None:
    """仅允许可安全点击的 HTTP(S) 链接。"""
    normalized = str(value or "").strip()
    if not normalized:
        return None
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name}必须是完整的 http/https 链接")
    return normalized[:500]
