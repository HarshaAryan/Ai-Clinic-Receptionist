"""
ClinicOS — Appointment slot generator.
Computes available slots based on clinic settings minus existing bookings.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from services.logger import logger

# Day name → Python weekday int (Monday=0 … Sunday=6)
_DAY_MAP = {
    "MON": 0, "TUE": 1, "WED": 2, "THU": 3,
    "FRI": 4, "SAT": 5, "SUN": 6,
}


def generate_available_slots(
    settings: Dict[str, Any],
    booked_times: List[datetime],
    from_date: Optional[datetime] = None,
    days_ahead: int = 7,
) -> List[datetime]:
    """
    Generate a list of available slot start-times for a clinic.

    Args:
        settings: clinic_settings row (working_days, start_hour, end_hour, slot_duration_minutes)
        booked_times: list of already-booked start_time datetimes
        from_date: start scanning from this datetime (default: now)
        days_ahead: how many days into the future to scan

    Returns:
        Sorted list of available datetime slots.
    """
    working_days = settings.get("working_days") or ["MON", "TUE", "WED", "THU", "FRI"]
    start_hour = int(settings.get("start_hour", 10))
    end_hour = int(settings.get("end_hour", 18))
    slot_minutes = int(settings.get("slot_duration_minutes", 30))

    allowed_weekdays = {_DAY_MAP[d.upper()] for d in working_days if d.upper() in _DAY_MAP}
    booked_set = {dt.replace(second=0, microsecond=0) for dt in booked_times}

    now = from_date or datetime.utcnow()
    base_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    slots: List[datetime] = []

    for day_offset in range(days_ahead):
        day = base_date + timedelta(days=day_offset)
        if day.weekday() not in allowed_weekdays:
            continue

        current = day.replace(hour=start_hour, minute=0)
        day_end = day.replace(hour=end_hour, minute=0)

        while current + timedelta(minutes=slot_minutes) <= day_end:
            if current > now and current not in booked_set:
                slots.append(current)
            current += timedelta(minutes=slot_minutes)

    logger.debug("Generated %d available slots over %d days", len(slots), days_ahead)
    return slots


def format_slots_text(slots: List[datetime], max_display: int = 10) -> str:
    """Format slot list as a human-readable string for Gemini prompts."""
    if not slots:
        return "(No available slots found in the next week.)"

    lines = [s.strftime("%a %d %b — %I:%M %p") for s in slots[:max_display]]
    text = "\n".join(f"  • {line}" for line in lines)
    remaining = len(slots) - max_display
    if remaining > 0:
        text += f"\n  ... and {remaining} more slots available."
    return text
