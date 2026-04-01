from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class MemoryType(Enum):
    USER = "user"
    PROJECT = "project"
    FEEDBACK = "feedback"
    REFERENCE = "reference"
    UNKNOWN = "unknown"

    @classmethod
    def from_str(cls, value: str) -> "MemoryType":
        try:
            return cls(value.lower())
        except ValueError:
            return cls.UNKNOWN


@dataclass
class MemoryFile:
    path: Path
    name: str
    description: str
    memory_type: MemoryType
    content: str
    modified: datetime
    scope: str = "local"  # "local" or "global"

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def type_label(self) -> str:
        return self.memory_type.value


@dataclass
class Project:
    dir_name: str
    display_name: str
    path: Path
    memory_files: list[MemoryFile] = field(default_factory=list)
    transcript_count: int = 0
    last_active: datetime | None = None

    @property
    def memory_path(self) -> Path:
        return self.path / "memory"

    @property
    def short_name(self) -> str:
        parts = self.display_name.rstrip("/").split("/")
        return parts[-1] if parts[-1] else "~"


@dataclass
class ClaudeSettings:
    raw: dict
    auto_dream_enabled: bool = False

    @property
    def allow_rules(self) -> list[str]:
        return self.raw.get("permissions", {}).get("allow", [])

    @property
    def deny_rules(self) -> list[str]:
        return self.raw.get("permissions", {}).get("deny", [])

    @property
    def enabled_plugins(self) -> dict[str, bool]:
        return self.raw.get("enabledPlugins", {})

    @property
    def hooks(self) -> dict:
        return self.raw.get("hooks", {})


@dataclass
class Skill:
    path: Path
    name: str
    description: str
    auto_triggers: list[str]
    content: str = ""
    scope: str = "global"  # "global" or "local"

    @property
    def is_active(self) -> bool:
        return len(self.auto_triggers) > 0


@dataclass
class Agent:
    path: Path
    name: str
    description: str
    model: str
    color: str
    content: str = ""
    scope: str = "global"  # "global" or "local"

    @property
    def short_description(self) -> str:
        first_line = self.description.split("\n")[0] if self.description else ""
        return first_line[:80]


@dataclass
class Command:
    """A custom slash command (.md file) from commands/ directories."""
    path: Path
    name: str
    scope: str  # "global" or "project"
    content: str = ""


@dataclass
class HistoryEntry:
    display: str
    timestamp: int
    project: str


@dataclass
class TranscriptSession:
    """A session transcript (.jsonl file) in a project directory."""
    path: Path
    session_id: str
    modified: datetime
    size_kb: int


@dataclass
class SessionMeta:
    pid: int
    session_id: str
    cwd: str
    started_at: int
    kind: str = "interactive"
    entrypoint: str = "cli"

    @property
    def short_cwd(self) -> str:
        parts = self.cwd.rstrip("/").split("/")
        return parts[-1] if parts[-1] else "~"
