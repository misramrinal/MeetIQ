"""Parse chat log files into a list of message dicts.

Supported formats (auto-detected):
  - Slack JSON export  ({"messages": [{"user": ..., "text": ..., "ts": "1234567890.123"}]})
  - Zoom/Teams plain text ([HH:MM:SS] Name: message  or  Name: message)
  - Generic plain text  (one message per non-empty line)
"""
from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

# Matches lines like "[10:25:33] Alice: hello" or "[1:05:03] Bob: yes"
_TIMESTAMPED_LINE = re.compile(r"^\[(\d{1,2}:\d{2}:\d{2})\]\s+([^:]+?):\s+(.+)$")
# Matches lines like "Alice: hello world"
_NAMED_LINE = re.compile(r"^([A-Za-z][^:]{0,80}):\s+(.+)$")


def parse_chat_file(file_bytes: bytes, filename: str) -> list[dict]:
    """Return a list of {sender, text, timestamp, platform} dicts."""
    name_lower = (filename or "").lower()
    if name_lower.endswith(".json"):
        result = _try_slack_json(file_bytes)
        if result is not None:
            return result
    # Fall through to line-based parsing for .txt, .log, and unrecognised JSON
    return _parse_line_based(file_bytes)


# ── Slack JSON ────────────────────────────────────────────────────────────

def _try_slack_json(file_bytes: bytes) -> list[dict] | None:
    try:
        data = json.loads(file_bytes)
    except Exception:
        return None

    messages = None
    if isinstance(data, list):
        messages = data
    elif isinstance(data, dict) and "messages" in data:
        messages = data["messages"]
    else:
        return None

    results = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        text = (m.get("text") or "").strip()
        if not text:
            continue
        ts_raw = m.get("ts") or m.get("timestamp")
        ts = None
        try:
            ts = float(ts_raw) if ts_raw else None
        except (TypeError, ValueError):
            pass
        sender = (
            m.get("user_profile", {}).get("display_name")
            or m.get("user_profile", {}).get("real_name")
            or m.get("username")
            or m.get("user")
            or None
        )
        results.append({
            "sender": sender,
            "text": text,
            "timestamp": ts,
            "platform": "slack",
        })
    return results if results else None


# ── Line-based (plain text / Zoom / Teams) ────────────────────────────────

def _parse_line_based(file_bytes: bytes) -> list[dict]:
    try:
        text = file_bytes.decode("utf-8", errors="replace")
    except Exception:
        return []

    results = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        m = _TIMESTAMPED_LINE.match(line)
        if m:
            time_str, sender, message = m.group(1), m.group(2).strip(), m.group(3).strip()
            ts = _hms_to_seconds(time_str)
            results.append({"sender": sender, "text": message, "timestamp": ts, "platform": "text"})
            continue

        m = _NAMED_LINE.match(line)
        if m:
            sender, message = m.group(1).strip(), m.group(2).strip()
            results.append({"sender": sender, "text": message, "timestamp": None, "platform": "text"})
            continue

        results.append({"sender": None, "text": line, "timestamp": None, "platform": "text"})

    return results


def _hms_to_seconds(hms: str) -> float | None:
    parts = hms.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        pass
    return None
