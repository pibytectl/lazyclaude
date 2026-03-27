"""LazyClaude — LazyGit-inspired TUI for managing the .claude ecosystem."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
from textual.widgets import Footer, Header

from lazyclaude.claude_dir import ClaudeDir
from lazyclaude.models import Agent, MemoryFile, MemoryType, Project, Skill
from lazyclaude.theme import OLED_THEME
from lazyclaude.widgets.detail_pane import DetailPane
from lazyclaude.widgets.help_overlay import HelpOverlay
from lazyclaude.widgets.memory_browser import ConfirmModal, NewMemoryModal
from lazyclaude.widgets.panel_widget import (
    AgentPanel,
    ConfigPanel,
    MemoryPanel,
    PanelWidget,
    ProjectPanel,
    SessionPanel,
    SkillPanel,
)

# Debounce delay for detail pane updates (seconds)
DETAIL_DEBOUNCE = 0.12


class LazyClaude(App):
    CSS = OLED_THEME
    TITLE = "LazyClaude"
    SUB_TITLE = "v0.2.0"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "help", "Help", key_display="?"),
        Binding("ctrl+r", "reload", "Reload"),
        Binding("ctrl+s", "save", "Save", show=False),
        Binding("1", "focus_panel_1", "Projects", show=False),
        Binding("2", "focus_panel_2", "Config", show=False),
        Binding("3", "focus_panel_3", "Memory", show=False),
        Binding("4", "focus_panel_4", "Skills", show=False),
        Binding("5", "focus_panel_5", "Agents", show=False),
        Binding("6", "focus_panel_6", "Sessions", show=False),
        Binding("tab", "focus_next", "Next", show=False),
        Binding("shift+tab", "focus_previous", "Prev", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._claude_dir = ClaudeDir()
        self._active_panel: PanelWidget | None = None
        self._selected_project: Project | None = None
        self._detail_timer: Timer | None = None
        self._pending_highlight: tuple[PanelWidget, object] | None = None
        self._claude_md_cache: dict[str, str] = {}  # project path → content

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        projects = self._claude_dir.list_projects()
        skills = self._claude_dir.list_skills()
        agents = self._claude_dir.list_agents()

        with Horizontal(id="main-layout"):
            with Vertical(id="left-panels"):
                yield ProjectPanel(projects, id="panel-projects")
                yield ConfigPanel(id="panel-config")
                yield MemoryPanel(id="panel-memory")
                yield SkillPanel(skills, id="panel-skills")
                yield AgentPanel(agents, id="panel-agents")
                yield SessionPanel(id="panel-sessions")
            yield DetailPane(id="detail-pane")

        yield Footer()

    def on_mount(self) -> None:
        # Load session data
        history = self._claude_dir.load_history(limit=500)
        sessions = self._claude_dir.list_sessions()
        self.query_one("#panel-sessions", SessionPanel).load_data(history, sessions)

        # Focus first panel and expand it
        panel = self.query_one("#panel-projects", ProjectPanel)
        self._set_active_panel(panel)
        panel.listview.focus()

        # Show initial detail
        detail = self.query_one("#detail-pane", DetailPane)
        detail.border_title = "Detail"
        detail.show_markdown("Welcome", "# LazyClaude v0.2.0\n\nSelect a project to get started.\n\n**Keys:** `1-6` switch panels, `?` help, `q` quit")

    # ── Panel Focus Management ────────────────────────────────────────────

    def _set_active_panel(self, panel: PanelWidget) -> None:
        if self._active_panel is panel:
            return
        # Collapse previous
        if self._active_panel is not None:
            self._active_panel.remove_class("panel-expanded")
        # Expand new
        self._active_panel = panel
        panel.add_class("panel-expanded")

    def on_descendant_focus(self, event) -> None:
        """Detect which panel contains the focused widget and expand it."""
        widget = event.widget
        # Walk up to find the PanelWidget ancestor
        current = widget
        while current is not None:
            if isinstance(current, PanelWidget):
                self._set_active_panel(current)
                break
            current = current.parent

    # ── Panel Item Events ─────────────────────────────────────────────────

    def on_panel_widget_item_highlighted(self, event: PanelWidget.ItemHighlighted) -> None:
        """Debounce detail pane updates — avoids heavy Markdown re-render on every j/k."""
        self._pending_highlight = (event.panel, event.data)
        if self._detail_timer is not None:
            self._detail_timer.stop()
        self._detail_timer = self.set_timer(DETAIL_DEBOUNCE, self._flush_highlight)

    def _flush_highlight(self) -> None:
        """Actually update the detail pane after debounce delay."""
        if self._pending_highlight is None:
            return
        panel, data = self._pending_highlight
        self._pending_highlight = None
        detail = self.query_one("#detail-pane", DetailPane)

        if isinstance(panel, ProjectPanel) and isinstance(data, Project):
            # Lightweight summary on highlight — CLAUDE.md loads on Enter
            mem_count = len(data.memory_files) if data.memory_files else 0
            detail.show_text(
                data.short_name,
                f"[cyan]Path:[/cyan]     {data.display_name}\n"
                f"[cyan]Sessions:[/cyan] {data.transcript_count}\n"
                f"[cyan]Memory:[/cyan]   {mem_count} files\n"
                f"[cyan]Active:[/cyan]   {data.last_active.strftime('%Y-%m-%d %H:%M') if data.last_active else 'never'}\n"
                f"\n[dim]Press Enter to load project[/dim]",
            )

        elif isinstance(panel, ConfigPanel) and isinstance(data, str):
            self._show_config_detail(data, detail)

        elif isinstance(panel, MemoryPanel) and isinstance(data, MemoryFile):
            detail.show_markdown(
                f"Memory — {data.name}",
                f"**Type:** {data.memory_type.value} | **File:** `{data.filename}`\n\n---\n\n{data.content}",
            )

        elif isinstance(panel, SkillPanel) and isinstance(data, Skill):
            # Lazy-load content if not yet loaded
            if not data.content:
                data.content = data.path.read_text(encoding="utf-8").split("---", 2)[-1].lstrip("\n") if data.path.exists() else ""
            triggers = ", ".join(f"`{t}`" for t in data.auto_triggers) if data.auto_triggers else "*none*"
            detail.show_markdown(
                f"Skill — {data.name}",
                f"**Triggers:** {triggers}\n\n**Description:** {data.description}\n\n---\n\n{data.content}",
            )

        elif isinstance(panel, AgentPanel) and isinstance(data, Agent):
            # Lazy-load content if not yet loaded
            if not data.content:
                data.content = data.path.read_text(encoding="utf-8").split("---", 2)[-1].lstrip("\n") if data.path.exists() else ""
            detail.show_markdown(
                f"Agent — {data.name}",
                f"**Model:** `{data.model}` | **Color:** {data.color}\n\n---\n\n{data.content}",
            )

        elif isinstance(panel, SessionPanel):
            from lazyclaude.models import HistoryEntry, TranscriptSession
            if isinstance(data, TranscriptSession):
                detail.show_text(
                    f"Session — {data.session_id[:12]}…",
                    f"[cyan]Session ID:[/cyan] {data.session_id}\n"
                    f"[cyan]Modified:[/cyan]   {data.modified.strftime('%Y-%m-%d %H:%M')}\n"
                    f"[cyan]Size:[/cyan]       {data.size_kb} KB\n"
                    f"[cyan]Path:[/cyan]       {data.path}",
                )
            elif isinstance(data, HistoryEntry):
                detail.show_text(
                    f"History — {data.project.split('/')[-1]}",
                    f"[cyan]Command:[/cyan] {data.display}\n\n[dim]Project: {data.project}[/dim]",
                )

    def _get_claude_md(self, project: Project) -> str:
        """Cached CLAUDE.md loading."""
        key = str(project.path)
        if key not in self._claude_md_cache:
            self._claude_md_cache[key] = self._claude_dir.load_claude_md(project)
        return self._claude_md_cache[key]

    def on_panel_widget_item_selected(self, event: PanelWidget.ItemSelected) -> None:
        """Handle Enter key or action in panels."""
        panel = event.panel
        data = event.data
        detail = self.query_one("#detail-pane", DetailPane)

        # ── Project selection / actions ──
        if isinstance(panel, ProjectPanel):
            if isinstance(data, tuple) and data[0] == "action":
                self._handle_project_action(data[1])
            elif isinstance(data, Project):
                self._selected_project = data
                data.memory_files = self._claude_dir.load_memory_files(data)
                self.query_one("#panel-memory", MemoryPanel).load_files(data.memory_files)
                transcripts = self._claude_dir.list_transcripts(data)
                self.query_one("#panel-sessions", SessionPanel).load_transcripts(transcripts)
                self.sub_title = data.display_name
                # Show CLAUDE.md on Enter
                detail = self.query_one("#detail-pane", DetailPane)
                claude_md = self._get_claude_md(data)
                detail.show_markdown(
                    f"CLAUDE.md — {data.short_name}",
                    claude_md or f"*No CLAUDE.md for {data.display_name}*",
                )
                self.notify(f"Loaded {data.short_name}", timeout=2)

        # ── Config actions ──
        elif isinstance(panel, ConfigPanel):
            if isinstance(data, tuple) and data[0] == "edit":
                self._handle_config_edit(data[1])
            elif isinstance(data, str):
                self._show_config_detail(data, detail)

        # ── Memory actions ──
        elif isinstance(panel, MemoryPanel):
            if isinstance(data, tuple) and data[0] == "action":
                self._handle_memory_action(data[1])
            elif isinstance(data, MemoryFile):
                self._start_memory_edit(data)

        # ── Session actions ──
        elif isinstance(panel, SessionPanel):
            if isinstance(data, tuple) and data[0] == "action":
                self._handle_session_action(data[1])

    # ── Project Helpers ────────────────────────────────────────────────────

    def _handle_project_action(self, action: str) -> None:
        if action == "delete_project":
            proj_panel = self.query_one("#panel-projects", ProjectPanel)
            project = proj_panel.selected_project
            if project is None:
                return

            # Tally what will be deleted
            mem_count = 0
            mem_dir = project.memory_path
            if mem_dir.exists():
                from lazyclaude.claude_dir import IGNORED_MEMORY_FILES
                mem_count = sum(1 for f in mem_dir.iterdir()
                                if f.suffix == ".md" and f.name not in IGNORED_MEMORY_FILES)
            transcripts = self._claude_dir.list_transcripts(project)
            total_kb = sum(t.size_kb for t in transcripts)
            size = f"{total_kb}KB" if total_kb < 1024 else f"{total_kb // 1024}MB"

            msg = (
                f"Delete project '{project.short_name}'?\n"
                f"  {len(transcripts)} sessions ({size}), {mem_count} memory files\n"
                f"  Code at {project.display_name} is NOT deleted"
            )

            def on_confirm(confirmed: bool) -> None:
                if not confirmed:
                    return
                import shutil
                shutil.rmtree(project.path, ignore_errors=True)
                # Clear selection if this was the active project
                if self._selected_project is project:
                    self._selected_project = None
                    self.query_one("#panel-memory", MemoryPanel).load_files([])
                    self.query_one("#panel-sessions", SessionPanel).load_transcripts([])
                    self.sub_title = "v0.2.0"
                # Refresh project list
                self._claude_md_cache.pop(str(project.path), None)
                projects = self._claude_dir.list_projects()
                proj_panel.refresh_projects(projects)
                detail = self.query_one("#detail-pane", DetailPane)
                detail.show_text("Projects", f"[dim]Deleted {project.short_name}[/dim]")
                self.notify(f"Deleted {project.short_name}", severity="information", timeout=2)

            self.push_screen(ConfirmModal(msg), on_confirm)

    # ── Config Helpers ────────────────────────────────────────────────────

    def _show_config_detail(self, key: str, detail: DetailPane) -> None:
        if key == "claude_md":
            content = self._claude_dir.load_claude_md(self._selected_project)
            detail.show_markdown("CLAUDE.md", content or "*No CLAUDE.md*")
        elif key == "settings_json":
            settings = self._claude_dir.load_settings()
            detail.show_tree("settings.json", settings.raw)
        elif key == "settings_local":
            import json
            path = self._claude_dir.base / "settings.local.json"
            if path.exists():
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                    detail.show_tree("settings.local.json", raw)
                except Exception:
                    detail.show_text("settings.local.json", "[red]Error reading file[/red]")
            else:
                detail.show_text("settings.local.json", "[dim]File not found[/dim]")

    def _handle_config_edit(self, key: str) -> None:
        if key != "claude_md":
            self.notify("Only CLAUDE.md is editable", severity="warning", timeout=2)
            return
        detail = self.query_one("#detail-pane", DetailPane)
        content = self._claude_dir.load_claude_md(self._selected_project)
        detail.start_edit(content, title="CLAUDE.md")

    # ── Memory Helpers ────────────────────────────────────────────────────

    def _start_memory_edit(self, mem: MemoryFile) -> None:
        detail = self.query_one("#detail-pane", DetailPane)
        detail.start_edit(mem.content, title=f"Memory — {mem.name}")
        self._editing_memory = mem

    def _handle_memory_action(self, action: str) -> None:
        if self._selected_project is None:
            self.notify("Select a project first", severity="warning", timeout=2)
            return

        if action == "new_memory":
            def on_result(result: dict | None) -> None:
                if result is None or self._selected_project is None:
                    return
                self._claude_dir.create_memory_file(
                    project=self._selected_project,
                    filename=result["filename"],
                    name=result["name"],
                    memory_type=result["memory_type"],
                    description=result["description"],
                )
                files = self._claude_dir.load_memory_files(self._selected_project)
                self._selected_project.memory_files = files
                self.query_one("#panel-memory", MemoryPanel).load_files(files)
                self.notify("Memory file created", severity="information", timeout=2)

            self.push_screen(NewMemoryModal(), on_result)

        elif action == "delete_memory":
            mem_panel = self.query_one("#panel-memory", MemoryPanel)
            mem = mem_panel.selected_file
            if mem is None:
                self.notify("No file selected", severity="warning", timeout=2)
                return

            def on_confirm(confirmed: bool) -> None:
                if not confirmed or self._selected_project is None:
                    return
                self._claude_dir.delete_memory_file(mem, self._selected_project)
                files = self._claude_dir.load_memory_files(self._selected_project)
                self._selected_project.memory_files = files
                self.query_one("#panel-memory", MemoryPanel).load_files(files)
                detail = self.query_one("#detail-pane", DetailPane)
                detail.show_markdown("Memory", "*File deleted*")
                self.notify("Deleted", severity="information", timeout=2)

            self.push_screen(ConfirmModal(f"Delete '{mem.name}'?"), on_confirm)

    # ── Session Helpers ────────────────────────────────────────────────────

    def _handle_session_action(self, action: str) -> None:
        if action == "delete_session":
            session_panel = self.query_one("#panel-sessions", SessionPanel)
            transcript = session_panel.selected_transcript
            if transcript is None:
                self.notify("No session selected", severity="warning", timeout=2)
                return

            size = f"{transcript.size_kb}KB" if transcript.size_kb < 1024 else f"{transcript.size_kb // 1024}MB"
            date = transcript.modified.strftime("%Y-%m-%d %H:%M")

            def on_confirm(confirmed: bool) -> None:
                if not confirmed or self._selected_project is None:
                    return
                # Delete transcript file and its companion UUID directory
                transcript.path.unlink(missing_ok=True)
                companion_dir = transcript.path.parent / transcript.session_id
                if companion_dir.is_dir():
                    import shutil
                    shutil.rmtree(companion_dir, ignore_errors=True)
                # Refresh
                transcripts = self._claude_dir.list_transcripts(self._selected_project)
                session_panel.load_transcripts(transcripts)
                self._selected_project.transcript_count = len(transcripts)
                detail = self.query_one("#detail-pane", DetailPane)
                detail.show_text("Sessions", f"[dim]Session deleted ({size})[/dim]")
                self.notify(f"Deleted session ({size})", severity="information", timeout=2)

            self.push_screen(
                ConfirmModal(f"Delete session {transcript.session_id[:8]}…? ({size}, {date})"),
                on_confirm,
            )

    # ── Save ──────────────────────────────────────────────────────────────

    def action_save(self) -> None:
        detail = self.query_one("#detail-pane", DetailPane)
        if not detail.is_editing:
            return

        text = detail.get_edit_text()
        if text is None:
            return

        # Determine what we're editing
        editing_mem = getattr(self, "_editing_memory", None)
        if editing_mem is not None and isinstance(editing_mem, MemoryFile):
            editing_mem.content = text
            self._claude_dir.save_memory_file(editing_mem)
            detail.end_edit()
            detail.show_markdown(
                f"Memory — {editing_mem.name}",
                f"**Type:** {editing_mem.memory_type.value}\n\n---\n\n{text}",
            )
            self._editing_memory = None
            self.notify("Memory saved", severity="information", timeout=2)
        else:
            # Assume CLAUDE.md edit
            self._claude_dir.save_claude_md(text, self._selected_project)
            detail.end_edit()
            detail.show_markdown("CLAUDE.md", text)
            self.notify("CLAUDE.md saved", severity="information", timeout=2)

    # ── Global Actions ────────────────────────────────────────────────────

    def action_help(self) -> None:
        self.push_screen(HelpOverlay())

    def action_reload(self) -> None:
        self._claude_md_cache.clear()
        projects = self._claude_dir.list_projects()
        self.query_one("#panel-projects", ProjectPanel).refresh_projects(projects)

        skills = self._claude_dir.list_skills()
        self.query_one("#panel-skills", SkillPanel)._skills = skills
        self.query_one("#panel-skills", SkillPanel)._render_items()

        agents = self._claude_dir.list_agents()
        self.query_one("#panel-agents", AgentPanel)._agents = agents
        self.query_one("#panel-agents", AgentPanel)._render_items()

        history = self._claude_dir.load_history(limit=500)
        sessions = self._claude_dir.list_sessions()
        self.query_one("#panel-sessions", SessionPanel).load_data(history, sessions)

        self.notify("Reloaded", severity="information", timeout=2)

    def action_focus_panel_1(self) -> None:
        self._focus_panel("#panel-projects")

    def action_focus_panel_2(self) -> None:
        self._focus_panel("#panel-config")

    def action_focus_panel_3(self) -> None:
        self._focus_panel("#panel-memory")

    def action_focus_panel_4(self) -> None:
        self._focus_panel("#panel-skills")

    def action_focus_panel_5(self) -> None:
        self._focus_panel("#panel-agents")

    def action_focus_panel_6(self) -> None:
        self._focus_panel("#panel-sessions")

    def _focus_panel(self, selector: str) -> None:
        try:
            panel = self.query_one(selector, PanelWidget)
            self._set_active_panel(panel)
            panel.listview.focus()
        except Exception:
            pass


def main() -> None:
    LazyClaude().run()


if __name__ == "__main__":
    main()
