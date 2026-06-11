"""Topic segments in long chats — split on new-task cues."""

from __future__ import annotations

from lib.lang_cues import build_new_task_pattern, load_lang_cues

_NEW_TASK = build_new_task_pattern(load_lang_cues())


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
