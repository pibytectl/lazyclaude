from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widgets import ContentSwitcher, Label, Markdown, TextArea, Tree
from textual.widgets.tree import TreeNode
from textual.widget import Widget

from lazyclaude.claude_dir import ClaudeDir
from lazyclaude.models import ClaudeSettings, Project


def _populate_tree(node: TreeNode, value: object) -> None:
    """Recursively populate a Tree from a JSON-like structure."""
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                child = node.add(str(k), expand=False)
                _populate_tree(child, v)
            else:
                node.add_leaf(f"{k}: {v!r}")
    elif isinstance(value, list):
        # Group string allow/deny rules by tool type prefix
        if all(isinstance(i, str) for i in value):
            grouped: dict[str, list[str]] = {}
            for item in value:
                prefix = item.split("(")[0] if "(" in item else item.split(" ")[0]
                grouped.setdefault(prefix, []).append(item)
            for prefix, items in sorted(grouped.items()):
                if len(items) == 1:
                    node.add_leaf(items[0])
                else:
                    grp = node.add(f"{prefix} ({len(items)})", expand=False)
                    for item in items:
                        grp.add_leaf(item)
        else:
            for i, item in enumerate(value):
                if isinstance(item, (dict, list)):
                    child = node.add(f"[{i}]", expand=False)
                    _populate_tree(child, item)
                else:
                    node.add_leaf(repr(item))
    else:
        node.add_leaf(repr(value))


class ConfigViewer(Widget):
    BINDINGS = [
        Binding("e", "toggle_edit", "Edit CLAUDE.md"),
        Binding("h", "show_claude", "CLAUDE.md", show=False),
        Binding("l", "show_settings", "Settings", show=False),
        Binding("escape", "cancel_edit", "Cancel", show=False),
    ]

    class Saved(Message):
        pass

    DEFAULT_CSS = """
    ConfigViewer {
        height: 1fr;
    }
    ConfigViewer Label.switcher-tabs {
        height: 1;
        background: #0a0a0a;
        color: #555555;
        padding: 0 1;
    }
    ConfigViewer ContentSwitcher {
        height: 1fr;
    }
    """

    def __init__(self, claude_dir: ClaudeDir, **kwargs) -> None:
        super().__init__(**kwargs)
        self._claude_dir = claude_dir
        self._project: Project | None = None
        self._editing = False
        self._content = ""
        self._settings: ClaudeSettings | None = None
        self._active_view = "claude"

    def compose(self) -> ComposeResult:
        yield Label(
            " [bold cyan]CLAUDE.md[/bold cyan] [dim](e=edit)[/dim]  [dim]h/l to switch[/dim]",
            classes="switcher-tabs",
        )
        with ContentSwitcher(initial="view-claude"):
            yield Markdown("", id="view-claude")
            yield Tree("settings.json", id="view-settings")

    def on_mount(self) -> None:
        self._load_content()

    def _load_content(self) -> None:
        self._content = self._claude_dir.load_claude_md(self._project)
        self._settings = self._claude_dir.load_settings()
        self._render_markdown()
        self._render_settings_tree()

    def _render_markdown(self) -> None:
        try:
            md = self.query_one("#view-claude", Markdown)
            md.update(self._content or "*No CLAUDE.md found for this project — showing global*\n\n*(Select a project that has a CLAUDE.md, or create one)*")
        except Exception:
            pass

    def _render_settings_tree(self) -> None:
        try:
            tree = self.query_one("#view-settings", Tree)
            tree.clear()
            if self._settings and self._settings.raw:
                _populate_tree(tree.root, self._settings.raw)
                tree.root.expand()
        except Exception:
            pass

    def load_project(self, project: Project) -> None:
        self._project = project
        if self._editing:
            self._cancel_edit()
        self._load_content()
        # Update tab label
        try:
            has_claude = bool(self._content)
            status = "" if has_claude else " [dim](none)[/dim]"
            self.query_one(".switcher-tabs", Label).update(
                f" [bold cyan]CLAUDE.md{status}[/bold cyan] [dim](e=edit)[/dim]  "
                f"[dim]settings.json[/dim]  [dim]h/l switch[/dim]"
            )
        except Exception:
            pass

    def action_show_claude(self) -> None:
        self._active_view = "claude"
        self.query_one(ContentSwitcher).current = "view-claude"

    def action_show_settings(self) -> None:
        self._active_view = "settings"
        self.query_one(ContentSwitcher).current = "view-settings"

    def action_toggle_edit(self) -> None:
        if self._active_view != "claude":
            self.action_show_claude()
            return
        if not self._editing:
            self._start_edit()
        else:
            self._save_edit()

    def _start_edit(self) -> None:
        self._editing = True
        md = self.query_one("#view-claude", Markdown)
        md.display = False
        editor = TextArea(
            self._content,
            id="claude-editor",
            language="markdown",
        )
        self.query_one(ContentSwitcher).mount(editor)
        self.query_one(ContentSwitcher).current = "claude-editor"
        editor.focus()
        self.notify("Editing CLAUDE.md — Ctrl+S to save, Escape to cancel", timeout=3)

    def _save_edit(self) -> None:
        try:
            text_area = self.query_one("#claude-editor", TextArea)
        except Exception:
            return
        new_content = text_area.text
        self._claude_dir.save_claude_md(new_content, self._project)
        self._content = new_content
        text_area.remove()
        self._editing = False
        md = self.query_one("#view-claude", Markdown)
        md.display = True
        self.query_one(ContentSwitcher).current = "view-claude"
        md.update(self._content)
        self.notify("CLAUDE.md saved", severity="information", timeout=2)
        self.post_message(self.Saved())

    def _cancel_edit(self) -> None:
        try:
            self.query_one("#claude-editor", TextArea).remove()
        except Exception:
            pass
        self._editing = False
        try:
            md = self.query_one("#view-claude", Markdown)
            md.display = True
            self.query_one(ContentSwitcher).current = "view-claude"
        except Exception:
            pass

    def action_cancel_edit(self) -> None:
        if self._editing:
            self._cancel_edit()

    def on_key(self, event) -> None:
        if self._editing and event.key == "ctrl+s":
            self._save_edit()
            event.stop()
