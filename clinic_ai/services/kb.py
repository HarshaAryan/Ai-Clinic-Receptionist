from typing import List, Dict, Any


def render_kb(entries: List[Dict[str, Any]]) -> str:
    if not entries:
        return "(No clinic-specific knowledge provided.)"
    parts = []
    for item in entries:
        title = item.get("title") or ""
        content = item.get("content") or ""
        parts.append(f"- {title}: {content}".strip())
    return "\n".join(parts)
