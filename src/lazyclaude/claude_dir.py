import json
import shutil
from datetime import datetime
from pathlib import Path

import yaml

from lazyclaude.history import load_history, load_sessions
from lazyclaude.models import (
    Agent,
    ClaudeSettings,
    Command,
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
    """Convert '-home-andy-projects-claude-claude-local-dev' → '/home/andy/projects/claude/claude_local_dev'.

    Claude encodes paths by replacing both '/' and '_' with '-'.
    We rebuild the path greedily by checking actual directory contents at each level.
    """
    name = dir_name.lstrip("-")
    segments = name.split("-")
    return str(_resolve_segments(Path("/"), segments, 0))


def _resolve_segments(parent: Path, segments: list[str], start: int) -> Path:
    """Greedily resolve encoded segments against the real filesystem."""
    if start >= len(segments):
        return parent

    if not parent.is_dir():
        return parent / "/".join(segments[start:])

    try:
        children = {c.name for c in parent.iterdir() if c.is_dir()}
    except PermissionError:
        children = set()

    # Try longest match first (greedy) — check both hyphen and underscore joins
    for end in range(len(segments), start, -1):
        chunk = segments[start:end]
        for joiner in ("-", "_"):
            candidate = joiner.join(chunk)
            if candidate in children:
                result = _resolve_segments(parent / candidate, segments, end)
                if result.exists():
                    return result

    # Single segment, no match needed (e.g. 'home', 'andy')
    return _resolve_segments(parent / segments[start], segments, start + 1)


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

    def _load_memory_from_dir(self, mem_dir: Path, scope: str = "local") -> list[MemoryFile]:
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
                    scope=scope,
                ))
            except Exception:
                continue
        return files

    def load_memory_files(self, project: Project) -> list[MemoryFile]:
        return self._load_memory_from_dir(project.memory_path, scope="local")

    def load_global_memory_files(self) -> list[MemoryFile]:
        """Load memory from ~/.claude/memory/ (the main global memory directory)."""
        return self._load_memory_from_dir(self.base / "memory", scope="global")

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
        """Load CLAUDE.md for a project. Does NOT fall back to global."""
        if project is not None:
            decoded = project.display_name
            project_claude = Path(decoded) / "CLAUDE.md"
            if project_claude.exists():
                return project_claude.read_text(encoding="utf-8")
            return ""
        # No project specified — load global
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

    # ── Commands ──────────────────────────────────────────────────────────

    def list_commands(self, project: Project | None = None) -> list[Command]:
        """Discover custom slash commands from global and project commands/ dirs."""
        commands: list[Command] = []

        # Global commands: ~/.claude/commands/
        global_dir = self.base / "commands"
        if global_dir.exists():
            for f in sorted(global_dir.iterdir()):
                if f.suffix == ".md" and f.is_file():
                    commands.append(Command(
                        path=f,
                        name=f.stem,
                        scope="global",
                    ))

        # Project-scoped commands: ~/.claude/projects/<encoded>/commands/
        if project is not None:
            proj_cmd_dir = project.path / "commands"
            if proj_cmd_dir.exists():
                for f in sorted(proj_cmd_dir.iterdir()):
                    if f.suffix == ".md" and f.is_file():
                        commands.append(Command(
                            path=f,
                            name=f.stem,
                            scope="project",
                        ))

        return commands

    # ── Skills ────────────────────────────────────────────────────────────────

    def _load_skills_from(self, skills_dir: Path, scope: str = "global") -> list[Skill]:
        if not skills_dir.exists():
            return []
        skills: list[Skill] = []
        for entry in sorted(skills_dir.iterdir()):
            if not entry.is_dir():
                continue
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
                    content="",
                    scope=scope,
                ))
            except (OSError, Exception):
                continue
        return skills

    def list_skills(self, project: "Project | None" = None) -> list[Skill]:
        skills = self._load_skills_from(self.base / "skills", scope="global")
        if project is not None:
            local_dir = Path(project.display_name) / ".claude" / "skills"
            skills.extend(self._load_skills_from(local_dir, scope="local"))
        return skills

    # ── Agents ────────────────────────────────────────────────────────────────

    def list_agents(self, project: "Project | None" = None) -> list[Agent]:
        agents: list[Agent] = []
        # Global agents from ~/.claude/agents/
        agents_dir = self.base / "agents"
        if agents_dir.exists():
            agents.extend(self._load_agents_from(agents_dir, scope="global"))
        # Local agents from <project>/.claude/agents/
        if project:
            local_dir = Path(project.display_name) / ".claude" / "agents"
            if local_dir.exists():
                agents.extend(self._load_agents_from(local_dir, scope="local"))
        return agents

    def _load_agents_from(self, agents_dir: Path, scope: str = "global") -> list[Agent]:
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
                    scope=scope,
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
