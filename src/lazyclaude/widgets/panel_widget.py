"""Base PanelWidget and concrete panel implementations for the left sidebar."""

from __future__ import annotations

from datetime import datetime

from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import ListView, ListItem, Static
from textual.app import ComposeResult

from lazyclaude.claude_dir import IGNORED_MEMORY_FILES
from lazyclaude.models import Agent, HistoryEntry, MemoryFile, MemoryType, Project, Skill, TranscriptSession


# ── Utility ──────────────────────────────────────────────────────────────────


def _fmt_date(dt: datetime | None) -> str:
    if dt is None:
        return "never"
    now = datetime.now()
    delta = now - dt
    if delta.days == 0:
        return "0d"
    if delta.days == 1:
        return "1d"
    if delta.days < 7:
        return f"{delta.days}d"
    if delta.days < 30:
        return f"{delta.days // 7}w"
    return dt.strftime("%b %d")


def _fmt_ts(ts_ms: int) -> str:
    """Format a millisecond timestamp to relative date."""
    if ts_ms == 0:
        return "unknown"
    dt = datetime.fromtimestamp(ts_ms / 1000)
    return _fmt_date(dt)


TYPE_COLORS = {
    MemoryType.USER: "cyan",
    MemoryType.PROJECT: "red",
    MemoryType.FEEDBACK: "yellow",
    MemoryType.REFERENCE: "magenta",
    MemoryType.UNKNOWN: "white",
}

AGENT_COLORS = {
    "orange": "#ffa500",
    "blue": "#4ecdc4",
    "green": "#00d4aa",
    "cyan": "#00bcd4",
    "purple": "#a29bfe",
    "white": "#c0c0c0",
    "red": "#ff6b6b",
}

MODEL_COLORS = {
    "sonnet": "#feca57",
    "opus": "#ff6b6b",
    "haiku": "#4ecdc4",
}


# ── Base PanelWidget ─────────────────────────────────────────────────────────


class PanelWidget(Widget):
    """Base class for all left-side panels in the LazyGit-style layout."""

    class ItemHighlighted(Message):
        """Posted when the highlighted item changes in any panel."""

        def __init__(self, panel: PanelWidget, data: object) -> None:
            super().__init__()
            self.panel = panel
            self.data = data

    class ItemSelected(Message):
        """Posted when an item is selected (Enter) in any panel."""

        def __init__(self, panel: PanelWidget, data: object) -> None:
            super().__init__()
            self.panel = panel
            self.data = data

    panel_index: int = 0
    panel_label: str = "Panel"
    subtabs: list[str] = []
    _active_subtab: int = 0

    BINDINGS = [
        Binding("left_square_bracket", "prev_subtab", "[ prev tab", show=False),
        Binding("right_square_bracket", "next_subtab", "] next tab", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield ListView(id=f"panel-list-{self.panel_index}")

    def on_mount(self) -> None:
        self._update_title()
        self._render_items()

    @property
    def listview(self) -> ListView:
        return self.query_one(ListView)

    def _update_title(self) -> None:
        label = f"{self.panel_index} {self.panel_label}"
        if self.subtabs:
            parts = []
            for i, tab in enumerate(self.subtabs):
                if i == self._active_subtab:
                    parts.append(f"[bold]{tab}[/bold]")
                else:
                    parts.append(f"[dim]{tab}[/dim]")
            label += " [dim]·[/dim] " + " [dim]|[/dim] ".join(parts)
        self.border_title = label

    def _render_items(self) -> None:
        """Override in subclasses to populate the ListView."""
        pass

    def _post_highlight(self, data: object) -> None:
        self.post_message(self.ItemHighlighted(self, data))

    def _post_select(self, data: object) -> None:
        self.post_message(self.ItemSelected(self, data))

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        data = getattr(event.item, "data", None)
        if data is not None:
            self._post_highlight(data)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        data = getattr(event.item, "data", None)
        if data is not None:
            self._post_select(data)

    def action_prev_subtab(self) -> None:
        if not self.subtabs:
            return
        self._active_subtab = (self._active_subtab - 1) % len(self.subtabs)
        self._update_title()
        self._render_items()

    def action_next_subtab(self) -> None:
        if not self.subtabs:
            return
        self._active_subtab = (self._active_subtab + 1) % len(self.subtabs)
        self._update_title()
        self._render_items()

    def _make_item(self, label: str, data: object) -> ListItem:
        item = ListItem(Static(label, markup=True))
        item.data = data  # type: ignore[attr-defined]
        return item


# ── ProjectPanel ─────────────────────────────────────────────────────────────


class ProjectPanel(PanelWidget):
    panel_index = 1
    panel_label = "Projects"

    BINDINGS = [
        Binding("enter", "select_cursor", "Select", show=True),
        Binding("d", "delete_project", "Delete", show=True),
        *PanelWidget.BINDINGS,
    ]

    def __init__(self, projects: list[Project], **kwargs) -> None:
        super().__init__(**kwargs)
        self._projects = projects

    def action_delete_project(self) -> None:
        idx = self.listview.index
        if idx is not None and idx < len(self._projects):
            self._post_select(("action", "delete_project"))

    @property
    def selected_project(self) -> Project | None:
        idx = self.listview.index
        if idx is not None and idx < len(self._projects):
            return self._projects[idx]
        return None

    def _render_items(self) -> None:
        lv = self.listview
        lv.clear()
        for project in self._projects:
            name = project.short_name
            if project.display_name in ("/home/andy", "/home/andy/"):
                name = "~ (Global)"
            if len(name) > 26:
                name = name[:25] + "…"
            date = _fmt_date(project.last_active)
            # Count memory files from disk (cheap — just counts .md files)
            mem_count = 0
            mem_dir = project.memory_path
            if mem_dir.exists():
                mem_count = sum(1 for f in mem_dir.iterdir()
                                if f.suffix == ".md" and f.name not in IGNORED_MEMORY_FILES)
            badges = []
            if project.transcript_count:
                badges.append(f"{project.transcript_count}s")
            if mem_count:
                badges.append(f"{mem_count}m")
            suffix = " ".join(badges)
            if suffix:
                suffix = " " + suffix
            label = f"{name} [dim]{date}{suffix}[/dim]"
            lv.append(self._make_item(label, project))

    def refresh_projects(self, projects: list[Project]) -> None:
        self._projects = projects
        self._render_items()


# ── ConfigPanel ──────────────────────────────────────────────────────────────


class ConfigPanel(PanelWidget):
    panel_index = 2
    panel_label = "Config"

    BINDINGS = [
        Binding("e", "edit_config", "Edit", show=True),
        Binding("enter", "select_cursor", "View", show=True),
        *PanelWidget.BINDINGS,
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._project: Project | None = None
        self._config_items: list[tuple[str, str]] = []
        self._rebuild_items()

    def _rebuild_items(self) -> None:
        """Rebuild config item list based on current project."""
        from pathlib import Path

        items: list[tuple[str, str]] = []

        # Project CLAUDE.md
        if self._project:
            proj_path = Path(self._project.display_name) / "CLAUDE.md"
            exists = proj_path.exists()
            name = self._project.short_name
            if exists:
                items.append((f"[cyan]CLAUDE.md[/cyan] [dim]({name})[/dim]", "claude_md"))
            else:
                items.append((f"[dim]CLAUDE.md ({name}) — none[/dim]", "claude_md"))
        else:
            items.append(("[dim]CLAUDE.md — select a project[/dim]", "claude_md"))

        # Global CLAUDE.md
        items.append(("[cyan]CLAUDE.md[/cyan] [dim](global)[/dim]", "claude_md_global"))

        # Settings
        items.append(("settings.json", "settings_json"))
        items.append(("settings.local.json", "settings_local"))

        self._config_items = items

    def load_project(self, project: Project) -> None:
        self._project = project
        self._rebuild_items()
        self._render_items()

    def _render_items(self) -> None:
        lv = self.listview
        lv.clear()
        for display, key in self._config_items:
            lv.append(self._make_item(display, key))

    def action_edit_config(self) -> None:
        idx = self.listview.index
        if idx is not None and idx < len(self._config_items):
            self._post_select(("edit", self._config_items[idx][1]))


# ── MemoryPanel ──────────────────────────────────────────────────────────────


class MemoryPanel(PanelWidget):
    panel_index = 3
    panel_label = "Memory"

    BINDINGS = [
        Binding("enter", "select_cursor", "Edit", show=True),
        Binding("n", "new_memory", "New", show=True),
        Binding("d", "delete_memory", "Delete", show=True),
        *PanelWidget.BINDINGS,
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._memory_files: list[MemoryFile] = []

    def load_files(self, files: list[MemoryFile]) -> None:
        self._memory_files = files
        self._render_items()

    def _render_items(self) -> None:
        lv = self.listview
        lv.clear()
        if not self._memory_files:
            lv.append(self._make_item("[dim]No memory files[/dim]", None))
            return
        type_labels = {
            MemoryType.USER: "USR",
            MemoryType.PROJECT: "PRJ",
            MemoryType.FEEDBACK: "FDB",
            MemoryType.REFERENCE: "REF",
            MemoryType.UNKNOWN: "UNK",
        }
        for mem in self._memory_files:
            color = TYPE_COLORS.get(mem.memory_type, "white")
            tag = type_labels.get(mem.memory_type, "UNK")
            name = mem.name
            if len(name) > 18:
                name = name[:17] + "…"
            label = f"[{color}]{tag}[/{color}] {name}"
            lv.append(self._make_item(label, mem))

    def action_new_memory(self) -> None:
        self._post_select(("action", "new_memory"))

    def action_delete_memory(self) -> None:
        self._post_select(("action", "delete_memory"))

    @property
    def selected_file(self) -> MemoryFile | None:
        idx = self.listview.index
        if idx is not None and idx < len(self._memory_files):
            return self._memory_files[idx]
        return None


# ── SkillPanel ───────────────────────────────────────────────────────────────


class SkillPanel(PanelWidget):
    panel_index = 4
    panel_label = "Skills"
    subtabs = ["All", "Active"]

    BINDINGS = [
        Binding("enter", "select_cursor", "View", show=True),
        *PanelWidget.BINDINGS,
    ]

    def __init__(self, skills: list[Skill], **kwargs) -> None:
        super().__init__(**kwargs)
        self._skills = skills

    def _render_items(self) -> None:
        lv = self.listview
        lv.clear()
        skills = self._skills
        if self._active_subtab == 1:  # Active only
            skills = [s for s in skills if s.is_active]
        if not skills:
            lv.append(self._make_item("[dim]No skills[/dim]", None))
            return
        for skill in skills:
            triggers = f" [dim]{len(skill.auto_triggers)} triggers[/dim]" if skill.auto_triggers else ""
            lv.append(self._make_item(f"{skill.name}{triggers}", skill))


# ── AgentPanel ───────────────────────────────────────────────────────────────


class AgentPanel(PanelWidget):
    panel_index = 5
    panel_label = "Agents"
    subtabs = ["All", "By Model"]

    BINDINGS = [
        Binding("enter", "select_cursor", "View", show=True),
        *PanelWidget.BINDINGS,
    ]

    def __init__(self, agents: list[Agent], **kwargs) -> None:
        super().__init__(**kwargs)
        self._agents = agents

    def _render_items(self) -> None:
        lv = self.listview
        lv.clear()
        if not self._agents:
            lv.append(self._make_item("[dim]No agents[/dim]", None))
            return

        if self._active_subtab == 1:  # By Model
            by_model: dict[str, list[Agent]] = {}
            for a in self._agents:
                by_model.setdefault(a.model, []).append(a)
            for model, agents in sorted(by_model.items()):
                mc = MODEL_COLORS.get(model, "#c0c0c0")
                lv.append(self._make_item(f"[{mc}]── {model} ──[/{mc}]", None))
                for a in agents:
                    ac = AGENT_COLORS.get(a.color, "#c0c0c0")
                    lv.append(self._make_item(f"  [{ac}]{a.name}[/{ac}]", a))
        else:  # All
            for a in self._agents:
                ac = AGENT_COLORS.get(a.color, "#c0c0c0")
                mc = MODEL_COLORS.get(a.model, "#c0c0c0")
                lv.append(self._make_item(
                    f"[{ac}]{a.name}[/{ac}] [{mc}]{a.model}[/{mc}]", a
                ))


# ── SessionPanel ─────────────────────────────────────────────────────────────


class SessionPanel(PanelWidget):
    panel_index = 6
    panel_label = "Sessions"
    subtabs = ["Sessions", "History"]

    BINDINGS = [
        Binding("enter", "select_cursor", "View", show=True),
        Binding("d", "delete_session", "Delete", show=True),
        *PanelWidget.BINDINGS,
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._all_history: list[HistoryEntry] = []
        self._transcripts: list[TranscriptSession] = []

    def action_delete_session(self) -> None:
        """Request deletion of the selected transcript."""
        if self._active_subtab != 0 or not self._transcripts:
            return
        idx = self.listview.index
        if idx is not None and idx < len(self._transcripts):
            self._post_select(("action", "delete_session"))

    @property
    def selected_transcript(self) -> TranscriptSession | None:
        if self._active_subtab != 0:
            return None
        idx = self.listview.index
        if idx is not None and idx < len(self._transcripts):
            return self._transcripts[idx]
        return None

    def load_data(self, history: list[HistoryEntry], sessions: list) -> None:
        self._all_history = history
        self._render_items()

    def load_transcripts(self, transcripts: list[TranscriptSession]) -> None:
        """Load transcript files for the selected project."""
        self._transcripts = transcripts
        self._render_items()

    def _render_items(self) -> None:
        lv = self.listview
        lv.clear()

        if self._active_subtab == 0:  # Sessions (transcript files)
            if not self._transcripts:
                lv.append(self._make_item("[dim]No sessions — select a project[/dim]", None))
                return
            for t in self._transcripts:
                date = _fmt_date(t.modified)
                size = f"{t.size_kb}KB" if t.size_kb < 1024 else f"{t.size_kb // 1024}MB"
                sid = t.session_id[:8]
                label = f"[dim]{date}[/dim] {sid}… [dim]{size}[/dim]"
                lv.append(self._make_item(label, t))

        else:  # History (all prompts from history.jsonl)
            if not self._all_history:
                lv.append(self._make_item("[dim]No history[/dim]", None))
                return
            seen: set[str] = set()
            for entry in reversed(self._all_history):
                display = entry.display.strip()[:35]
                if display in seen:
                    continue
                seen.add(display)
                ts = _fmt_ts(entry.timestamp)
                proj = entry.project.rstrip("/").split("/")[-1] or "~"
                label = f"[dim]{ts}[/dim] [cyan]{proj}[/cyan] {display}"
                lv.append(self._make_item(label, entry))
                if len(seen) >= 50:
                    break
