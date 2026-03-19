"""Tests for the slot generation service."""

from datetime import datetime, timedelta

from services.slots import format_slots_text, generate_available_slots


def _settings(**overrides):
    base = {
        "working_days": ["MON", "TUE", "WED", "THU", "FRI"],
        "start_hour": 10,
        "end_hour": 18,
        "slot_duration_minutes": 30,
    }
    base.update(overrides)
    return base


class TestGenerateSlots:
    def test_generates_slots_for_working_days(self):
        # Pick a Monday
        monday = datetime(2026, 3, 2, 8, 0, 0)  # Monday
        slots = generate_available_slots(_settings(), [], from_date=monday, days_ahead=1)
        # 10:00 to 18:00 with 30-min slots = 16 slots
        assert len(slots) == 16
        assert slots[0].hour == 10
        assert slots[0].minute == 0
        assert slots[-1].hour == 17
        assert slots[-1].minute == 30

    def test_skips_weekends(self):
        # Pick a Saturday
        saturday = datetime(2026, 3, 7, 8, 0, 0)
        slots = generate_available_slots(_settings(), [], from_date=saturday, days_ahead=1)
        assert len(slots) == 0

    def test_excludes_booked_slots(self):
        monday = datetime(2026, 3, 2, 8, 0, 0)
        booked = [datetime(2026, 3, 2, 10, 0, 0), datetime(2026, 3, 2, 11, 0, 0)]
        slots = generate_available_slots(_settings(), booked, from_date=monday, days_ahead=1)
        booked_times = {s for s in slots if s.hour == 10 and s.minute == 0}
        assert len(booked_times) == 0  # 10:00 was booked
        assert len(slots) == 14  # 16 - 2 booked

    def test_custom_slot_duration(self):
        monday = datetime(2026, 3, 2, 8, 0, 0)
        slots = generate_available_slots(
            _settings(slot_duration_minutes=60),
            [],
            from_date=monday,
            days_ahead=1,
        )
        # 10:00 to 18:00 with 60-min slots = 8 slots
        assert len(slots) == 8

    def test_multiple_days(self):
        monday = datetime(2026, 3, 2, 8, 0, 0)
        slots = generate_available_slots(_settings(), [], from_date=monday, days_ahead=7)
        # 5 working days × 16 slots = 80
        assert len(slots) == 80


class TestFormatSlots:
    def test_empty_slots(self):
        text = format_slots_text([])
        assert "No available slots" in text

    def test_formats_slots(self):
        slots = [
            datetime(2026, 3, 2, 10, 0),
            datetime(2026, 3, 2, 10, 30),
        ]
        text = format_slots_text(slots)
        assert "10:00 AM" in text
        assert "10:30 AM" in text

    def test_truncates_long_list(self):
        slots = [datetime(2026, 3, 2, 10, 0) + timedelta(minutes=30 * i) for i in range(20)]
        text = format_slots_text(slots, max_display=5)
        assert "more slots" in text
