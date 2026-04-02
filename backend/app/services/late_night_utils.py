"""
NightBite AI — Late Night Domain Utils

Centralized logic for the late-night window (10 PM – 4 AM).
All late-night detection and time labeling flows through here.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


# ── Late-night window definition ──────────────────────────────────────────────

LATE_NIGHT_START_HOUR = 22   # 10 PM
LATE_NIGHT_END_HOUR = 4      # 4 AM (exclusive)


def is_late_night(dt: datetime) -> bool:
    """
    Return True if the datetime falls within the late-night window (10 PM – 4 AM).

    Always evaluates in UTC hour to be consistent with stored timestamps.
    The window wraps around midnight: hours 22, 23, 0, 1, 2, 3 are late-night.
    """
    if dt is None:
        return False
    hour = dt.hour
    return hour >= LATE_NIGHT_START_HOUR or hour < LATE_NIGHT_END_HOUR


def hour_to_time_label(hour: int) -> str:
    """Convert 0-23 hour to human-readable label like '12 AM', '10 PM'."""
    if hour == 0:
        return "12 AM"
    if hour < 12:
        return f"{hour} AM"
    if hour == 12:
        return "12 PM"
    return f"{hour - 12} PM"


def hour_to_late_night_slot(hour: int) -> Optional[str]:
    """
    Return a late-night slot label for the given hour, or None if not late night.
    Slots: 10p, 11p, 12a, 1a, 2a, 3a, 4a
    """
    slots = {22: "10 PM", 23: "11 PM", 0: "12 AM", 1: "1 AM", 2: "2 AM", 3: "3 AM", 4: "4 AM"}
    return slots.get(hour)


def get_late_night_window_label(hour: int) -> str:
    """
    Return a window label for behavioral context.
    e.g. 22/23 → "10 PM – 12 AM", 0-1 → "12 AM – 2 AM", 2-3 → "2 AM – 4 AM"
    """
    if hour in (22, 23):
        return "10 PM – 12 AM"
    if hour in (0, 1):
        return "12 AM – 2 AM"
    if hour in (2, 3, 4):
        return "2 AM – 4 AM"
    return "Daytime"


def late_night_hours() -> list[int]:
    """Return the list of late-night hours (22, 23, 0, 1, 2, 3, 4)."""
    return [22, 23, 0, 1, 2, 3, 4]


def normalize_food_name(raw: Optional[str]) -> str:
    """
    Normalize a raw food name to a canonical display name.
    Strips extra whitespace, title-cases, truncates to 60 chars.
    """
    if not raw:
        return "Unknown"
    cleaned = " ".join(raw.strip().split())
    # Title case but preserve single-char words
    titled = " ".join(word.capitalize() for word in cleaned.split())
    return titled[:60]


def current_late_night_context() -> dict:
    """Return current time context for AI prompts."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    is_ln = is_late_night(now)
    label = hour_to_time_label(hour)

    if is_ln:
        if hour in (22, 23):
            context = "It is late evening / early night — food delivery window is active."
        elif hour in (0, 1):
            context = "It is past midnight — a high-risk window for late-night eating."
        else:
            context = "It is very late night (2 AM – 4 AM) — peak NCD risk window for food orders."
    else:
        context = "It is daytime — not the primary late-night risk window."

    return {
        "hour": hour,
        "label": label,
        "is_late_night": is_ln,
        "context_text": context,
        "window_label": get_late_night_window_label(hour),
    }
