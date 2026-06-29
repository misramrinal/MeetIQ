"""Parse chat log files into a list of message dicts.

Supported formats (auto-detected):
  - Slack JSON export  ({"messages": [{"user": ..., "text": ..., "ts": "1234567890.123"}]})
  - Zoom/Teams plain text ([HH:MM:SS] Name: message  or  Name: message)
  - CSV export         (columns auto-detected: timestamp, sender/name/user, text/message/body)
  - Generic plain text  (one message per non-empty line)
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re

logger = logging.getLogger(__name__)

# Matches lines like "[10:25:33] Alice: hello" or "[1:05:03] Bob: yes"
_TIMESTAMPED_LINE = re.compile(r"^\[(\d{1,2}:\d{2}:\d{2})\]\s+([^:]+?):\s+(.+)$")
# Matches lines like "Alice: hello world"
_NAMED_LINE = re.compile(r"^([A-Za-z][^:]{0,80}):\s+(.+)$")

# CSV column name candidates (checked case-insensitively)
_CSV_TIME_COLS = {"time", "timestamp", "ts", "date", "datetime"}
_CSV_SENDER_COLS = {"sender", "name", "user", "username", "author", "from", "speaker"}
_CSV_TEXT_COLS = {"text", "message", "body", "content", "msg", "chat"}


def parse_chat_file(file_bytes: bytes, filename: str) -> list[dict]:
    """Return a list of {sender, text, timestamp, platform} dicts."""
    name_lower = (filename or "").lower()
    if name_lower.endswith(".json"):
        result = _try_slack_json(file_bytes)
        if result is not None:
            return result
    if name_lower.endswith(".csv"):
        result = _try_csv(file_bytes)
        if result is not None:
            return result
    # Fall through to line-based parsing for .txt, .log, .csv fallback, and
    # unrecognised JSON
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
    # Return None (not []) when nothing was parsed so the caller falls through
    # to line-based parsing for JSON files that aren't Slack exports.
    return results if results else None


# ── CSV ───────────────────────────────────────────────────────────────────

def _try_csv(file_bytes: bytes) -> list[dict] | None:
    """Parse a CSV chat export.  Auto-detects timestamp, sender, and text columns."""
    try:
        text = file_bytes.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return None

        # Map known column names (case-insensitive) to roles
        cols = {f.strip().lower(): f for f in reader.fieldnames}
        time_col = next((cols[c] for c in _CSV_TIME_COLS if c in cols), None)
        sender_col = next((cols[c] for c in _CSV_SENDER_COLS if c in cols), None)
        text_col = next((cols[c] for c in _CSV_TEXT_COLS if c in cols), None)

        if text_col is None:
            return None  # Can't identify the message body column

        results = []
        for row in reader:
            msg_text = (row.get(text_col) or "").strip()
            if not msg_text:
                continue
            sender = (row.get(sender_col) or "").strip() or None if sender_col else None
            ts = None
            if time_col:
                raw_ts = (row.get(time_col) or "").strip()
                ts = _hms_to_seconds(raw_ts) if re.match(r"^\d{1,2}:\d{2}", raw_ts) else None
            results.append({
                "sender": sender,
                "text": msg_text,
                "timestamp": ts,
                "platform": "csv",
            })
        return results if results else None
    except Exception as e:
        logger.warning("CSV chat parsing failed: %s", e)
        return None


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
