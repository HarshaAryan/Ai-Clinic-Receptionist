"""Tests for the Reminder Agent — building reminder payloads."""

from datetime import datetime, timedelta

from agents.reminder import ReminderAgent


class TestBuildReminders:
    def test_builds_reminders_in_window(self):
        agent = ReminderAgent()
        now = datetime.utcnow()
        appointments = [
            {
                "id": "appt-1",
                "patient_id": "p-1",
                "patient_name": "Rahul",
                "patient_phone": "919999999999",
                "start_time": now + timedelta(hours=12),
            },
            {
                "id": "appt-2",
                "patient_id": "p-2",
                "patient_name": "Priya",
                "patient_phone": "918888888888",
                "start_time": now + timedelta(hours=48),  # outside 24h window
            },
        ]
        reminders = agent.build_reminders(appointments, "Test Clinic", hours_before=24)
        assert len(reminders) == 1
        assert reminders[0].patient_phone == "919999999999"

    def test_skips_past_appointments(self):
        agent = ReminderAgent()
        appointments = [
            {
                "id": "appt-past",
                "patient_id": "p-1",
                "patient_name": "Old",
                "patient_phone": "919999999999",
                "start_time": datetime.utcnow() - timedelta(hours=2),
            },
        ]
        reminders = agent.build_reminders(appointments, "Test Clinic", hours_before=24)
        assert len(reminders) == 0

    def test_skips_no_phone(self):
        agent = ReminderAgent()
        appointments = [
            {
                "id": "appt-nophone",
                "patient_id": "p-1",
                "patient_name": "NoPhone",
                "patient_phone": None,
                "start_time": datetime.utcnow() + timedelta(hours=12),
            },
        ]
        reminders = agent.build_reminders(appointments, "Test Clinic", hours_before=24)
        assert len(reminders) == 0

    def test_2_hour_window(self):
        agent = ReminderAgent()
        now = datetime.utcnow()
        appointments = [
            {
                "id": "appt-soon",
                "patient_id": "p-1",
                "patient_name": "Soon",
                "patient_phone": "919999999999",
                "start_time": now + timedelta(hours=1),
            },
        ]
        reminders = agent.build_reminders(appointments, "Test Clinic", hours_before=2)
        assert len(reminders) == 1
