"""Topic segments in long chats — split on new-task cues."""

from __future__ import annotations

import re

_NEW_TASK = re.compile(
    r"(?:^|\b)(?:"
    r"new task|different topic|switching to|let'?s move on|"
    r"\u043e\u0442\u0434\u0435\u043b\u044c\u043d\u0430\u044f \u0437\u0430\u0434\u0430\u0447\u0430|"
    r"\u0434\u0440\u0443\u0433\u0430\u044f \u0442\u0435\u043c\u0430|"
    r"\u043f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0438\u043c\u0441\u044f|"
    r"\u043d\u043e\u0432\u0430\u044f \u0437\u0430\u0434\u0430\u0447\u0430"
    r")\b",
    re.I,
)


def segment_messages(messages: list[str], *, max_segments: int = 6) -> list[dict]:
    """
    Split user messages into topic segments at new-task cues.
    Returns [{segment, start, count, preview}, ...].
    """
    if not messages:
        return []
    breaks = [0]
    for i, msg in enumerate(messages):
        if i > 0 and _NEW_TASK.search(msg):
            breaks.append(i)
    if breaks[-1] != 0:
        breaks.append(len(messages))
    else:
        breaks = [0, len(messages)]

    segments: list[dict] = []
    for idx in range(len(breaks) - 1):
        start = breaks[idx]
        end = breaks[idx + 1]
        chunk = messages[start:end]
        if not chunk:
            continue
        preview = chunk[0][:120].strip()
        if len(preview) > 117:
            preview = preview[:117] + "..."
        segments.append(
            {
                "segment": len(segments) + 1,
                "start": start,
                "count": len(chunk),
                "preview": preview or "(segment)",
            }
        )
        if len(segments) >= max_segments:
            break
    return segments if len(segments) > 1 else []
