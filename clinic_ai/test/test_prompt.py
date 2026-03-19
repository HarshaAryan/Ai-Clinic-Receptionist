from services.gemini import build_system_prompt


def test_prompt_includes_guardrails():
    prompt = build_system_prompt("Clinic A", "KB", "Slots")
    assert "medical advice" in prompt
    assert "112/911" in prompt
    assert "Available Slots" in prompt
