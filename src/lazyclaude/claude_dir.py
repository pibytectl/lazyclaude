import json
import shutil
from datetime import datetime
from pathlib import Path

import yaml

from lazyclaude.history import load_history, load_sessions
from lazyclaude.models import (
    Agent,
    ClaudeSettings,
    HistoryEntry,
    MemoryFile,
    MemoryType,
    Project,
    SessionMeta,
    Skill,
    TranscriptSession,
)

IGNORED_MEMORY_FILES = {".consolidate-lock", ".highwatermark", "MEMORY.md"}


def _decode_project_name(dir_name: str) -> str:
    """Convert '-home-andy-MAMRS' → '/home/andy/MAMRS'.

    Tries to find which path actually exists by progressively keeping more
    of the suffix as a single hyphenated segment. This handles directory names
    like 'claude-whatsapp-channel' that contain hyphens.
    """
    name = dir_name.lstrip("-")
    segments = name.split("-")

    # Try keeping the last N segments as a single name (most specific first)
    for keep_last in range(len(segments) - 1, 0, -1):
        prefix_segs = segments[: len(segments) - keep_last]
        suffix = "-".join(segments[len(segments) - keep_last :])
        candidate = "/" + "/".join(prefix_segs + [suffix])
        if Path(candidate).exists():
            return candidate

    # Fallback: replace all dashes with slashes
    return "/" + "/".join(segments)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body. Returns (frontmatter_dict, body)."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        fm = {}
    body = parts[2].lstrip("\n")
    return fm, body


def _build_frontmatter(fm: dict, body: str) -> str:
    """Reconstruct file content with frontmatter."""
    fm_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True).strip()
    return f"---\n{fm_str}\n---\n\n{body}"


class ClaudeDir:
    def __init__(self, base: Path | None = None):
        self.base = base or Path.home() / ".claude"
        self.projects_dir = self.base / "projects"
        self.backups_dir = self.base / "backups" / "lazyclaude"

    def _backup(self, path: Path) -> None:
        """Copy file to backup dir before overwriting."""
        if not path.exists():
            return
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = self.backups_dir / f"{path.name}.{ts}"
        shutil.copy2(path, dest)

    # ── Projects ─────────────────────────────────────────────────────────────

    def list_projects(self) -> list[Project]:
        if not self.projects_dir.exists():
            return []

        projects: list[Project] = []
        for entry in sorted(self.projects_dir.iterdir()):
            if not entry.is_dir():
                continue
            dir_name = entry.name
            display_name = _decode_project_name(dir_name)

            # Count transcripts, find last active
            jsonl_files = list(entry.glob("*.jsonl"))
            transcript_count = len(jsonl_files)
            last_active: datetime | None = None
            if jsonl_files:
                newest = max(jsonl_files, key=lambda f: f.stat().st_mtime)
                last_active = datetime.fromtimestamp(newest.stat().st_mtime)

            projects.append(Project(
                dir_name=dir_name,
                display_name=display_name,
                path=entry,
                transcript_count=transcript_count,
                last_active=last_active,
            ))

        # Sort by last active (most recent first), None last
        projects.sort(key=lambda p: p.last_active or datetime.min, reverse=True)
        return projects

    # ── Memory ───────────────────────────────────────────────────────────────

    def load_memory_files(self, project: Project) -> list[MemoryFile]:
        mem_dir = project.memory_path
        if not mem_dir.exists():
            return []

        files: list[MemoryFile] = []
        for f in sorted(mem_dir.iterdir()):
            if f.name in IGNORED_MEMORY_FILES or not f.suffix == ".md":
                continue
            try:
                text = f.read_text(encoding="utf-8")
                fm, body = _parse_frontmatter(text)
                files.append(MemoryFile(
                    path=f,
                    name=fm.get("name", f.stem),
                    description=fm.get("description", ""),
                    memory_type=MemoryType.from_str(fm.get("type", "unknown")),
                    content=body,
                    modified=datetime.fromtimestamp(f.stat().st_mtime),
                ))
            except Exception:
                continue

        return files

    def save_memory_file(self, mem: MemoryFile) -> None:
        self._backup(mem.path)
        fm = {
            "name": mem.name,
            "description": mem.description,
            "type": mem.memory_type.value,
        }
        mem.path.write_text(_build_frontmatter(fm, mem.content), encoding="utf-8")

    def create_memory_file(
        self,
        project: Project,
        filename: str,
        name: str,
        memory_type: MemoryType,
        description: str,
    ) -> MemoryFile:
        mem_dir = project.memory_path
        mem_dir.mkdir(parents=True, exist_ok=True)
        if not filename.endswith(".md"):
            filename += ".md"
        path = mem_dir / filename
        fm = {"name": name, "description": description, "type": memory_type.value}
        body = ""
        path.write_text(_build_frontmatter(fm, body), encoding="utf-8")
        mem = MemoryFile(
            path=path,
            name=name,
            description=description,
            memory_type=memory_type,
            content=body,
            modified=datetime.now(),
        )
        self._update_memory_index(project)
        return mem

    def delete_memory_file(self, mem: MemoryFile, project: Project) -> None:
        self._backup(mem.path)
        mem.path.unlink(missing_ok=True)
        self._update_memory_index(project)

    def _update_memory_index(self, project: Project) -> None:
        """Regenerate MEMORY.md index from current memory files."""
        mem_dir = project.memory_path
        if not mem_dir.exists():
            return
        lines: list[str] = []
        for f in sorted(mem_dir.iterdir()):
            if f.name in IGNORED_MEMORY_FILES or not f.suffix == ".md":
                continue
            try:
                text = f.read_text(encoding="utf-8")
                fm, _ = _parse_frontmatter(text)
                entry_name = fm.get("name", f.stem)
                description = fm.get("description", "")
                hook = description.split(".")[0][:80] if description else ""
                lines.append(f"- [{entry_name}]({f.name}) — {hook}")
            except Exception:
                continue
        index_path = mem_dir / "MEMORY.md"
        self._backup(index_path)
        index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ── CLAUDE.md ─────────────────────────────────────────────────────────────

    def load_claude_md(self, project: Project | None = None) -> str:
        if project is not None:
            # Check for project-level CLAUDE.md (in the actual project dir, not .claude/projects/)
            decoded = project.display_name
            project_claude = Path(decoded) / "CLAUDE.md"
            if project_claude.exists():
                return project_claude.read_text(encoding="utf-8")
        global_claude = self.base / "CLAUDE.md"
        if global_claude.exists():
            return global_claude.read_text(encoding="utf-8")
        return ""

    def save_claude_md(self, content: str, project: Project | None = None) -> None:
        if project is not None:
            decoded = project.display_name
            project_claude = Path(decoded) / "CLAUDE.md"
            if project_claude.exists():
                self._backup(project_claude)
                project_claude.write_text(content, encoding="utf-8")
                return
        global_claude = self.base / "CLAUDE.md"
        self._backup(global_claude)
        global_claude.write_text(content, encoding="utf-8")

    # ── Transcripts ────────────────────────────────────────────────────────────

    def list_transcripts(self, project: Project) -> list[TranscriptSession]:
        """List session transcript .jsonl files in a project directory."""
        if not project.path.exists():
            return []
        transcripts: list[TranscriptSession] = []
        for f in project.path.iterdir():
            if not f.suffix == ".jsonl" or not f.is_file():
                continue
            try:
                stat = f.stat()
                transcripts.append(TranscriptSession(
                    path=f,
                    session_id=f.stem,
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    size_kb=int(stat.st_size / 1024),
                ))
            except OSError:
                continue
        transcripts.sort(key=lambda t: t.modified, reverse=True)
        return transcripts

    # ── Skills ────────────────────────────────────────────────────────────────

    def list_skills(self) -> list[Skill]:
        skills_dir = self.base / "skills"
        if not skills_dir.exists():
            return []
        skills: list[Skill] = []
        for entry in sorted(skills_dir.iterdir()):
            if not entry.is_dir():
                continue
            # Resolve symlinks, skip broken ones
            try:
                resolved = entry.resolve()
                skill_md = resolved / "SKILL.md"
                if not skill_md.exists():
                    continue
                text = skill_md.read_text(encoding="utf-8")
                fm, body = _parse_frontmatter(text)
                triggers = fm.get("autoTrigger", [])
                if isinstance(triggers, str):
                    triggers = [triggers]
                skills.append(Skill(
                    path=skill_md,
                    name=fm.get("name", entry.name),
                    description=fm.get("description", ""),
                    auto_triggers=triggers,
                    content="",  # lazy-loaded on demand
                ))
            except (OSError, Exception):
                continue
        return skills

    # ── Agents ────────────────────────────────────────────────────────────────

    def list_agents(self) -> list[Agent]:
        agents_dir = self.base / "agents"
        if not agents_dir.exists():
            return []
        agents: list[Agent] = []
        for f in sorted(agents_dir.iterdir()):
            if not f.suffix == ".md":
                continue
            try:
                text = f.read_text(encoding="utf-8")
                fm, body = _parse_frontmatter(text)
                desc = fm.get("description", "")
                if isinstance(desc, str):
                    desc = desc.strip()
                agents.append(Agent(
                    path=f,
                    name=fm.get("name", f.stem),
                    description=desc,
                    model=fm.get("model", "sonnet"),
                    color=fm.get("color", "white"),
                    content="",  # lazy-loaded on demand
                ))
            except (OSError, Exception):
                continue
        return agents

    # ── History / Sessions ────────────────────────────────────────────────────

    def load_history(self, limit: int = 500) -> list[HistoryEntry]:
        return load_history(self.base, limit)

    def list_sessions(self) -> list[SessionMeta]:
        return load_sessions(self.base)

    # ── Settings ──────────────────────────────────────────────────────────────

    def load_settings(self) -> ClaudeSettings:
        path = self.base / "settings.json"
        if not path.exists():
            return ClaudeSettings(raw={})
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            raw = {}
        return ClaudeSettings(
            raw=raw,
            auto_dream_enabled=raw.get("autoDreamEnabled", False),
        )
