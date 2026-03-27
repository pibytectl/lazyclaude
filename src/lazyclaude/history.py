"""Parser for ~/.claude/history.jsonl and session metadata."""

import json
from pathlib import Path

from lazyclaude.models import HistoryEntry, SessionMeta


def load_history(base: Path, limit: int = 500) -> list[HistoryEntry]:
    """Load recent history entries from history.jsonl (tail-read for performance)."""
    path = base / "history.jsonl"
    if not path.exists():
        return []

    entries: list[HistoryEntry] = []
    try:
        lines = _tail_lines(path, limit)
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                display = obj.get("display", "").strip()
                if not display:
                    continue
                entries.append(HistoryEntry(
                    display=display,
                    timestamp=obj.get("timestamp", 0),
                    project=obj.get("project", ""),
                ))
            except (json.JSONDecodeError, KeyError):
                continue
    except OSError:
        pass

    return entries


def _tail_lines(path: Path, n: int) -> list[str]:
    """Read last n lines of a file efficiently."""
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        if size == 0:
            return []
        # Read in chunks from the end
        chunk_size = min(size, n * 200)  # estimate ~200 bytes per line
        f.seek(max(0, size - chunk_size))
        data = f.read().decode("utf-8", errors="replace")
        lines = data.split("\n")
        return lines[-n:] if len(lines) > n else lines


def load_sessions(base: Path) -> list[SessionMeta]:
    """Load session metadata from ~/.claude/sessions/*.json."""
    sessions_dir = base / "sessions"
    if not sessions_dir.exists():
        return []

    sessions: list[SessionMeta] = []
    try:
        for f in sorted(sessions_dir.iterdir(), reverse=True):
            if not f.suffix == ".json":
                continue
            try:
                obj = json.loads(f.read_text(encoding="utf-8"))
                sessions.append(SessionMeta(
                    pid=obj.get("pid", 0),
                    session_id=obj.get("sessionId", ""),
                    cwd=obj.get("cwd", ""),
                    started_at=obj.get("startedAt", 0),
                    kind=obj.get("kind", "interactive"),
                    entrypoint=obj.get("entrypoint", "cli"),
                ))
            except (json.JSONDecodeError, KeyError, OSError):
                continue
    except OSError:
        pass

    # Sort by start time, most recent first
    sessions.sort(key=lambda s: s.started_at, reverse=True)
    return sessions


def group_history_by_project(entries: list[HistoryEntry]) -> dict[str, list[HistoryEntry]]:
    """Group history entries by project path."""
    grouped: dict[str, list[HistoryEntry]] = {}
    for entry in entries:
        key = entry.project.rstrip("/").split("/")[-1] or "~"
        grouped.setdefault(key, []).append(entry)
    return grouped
