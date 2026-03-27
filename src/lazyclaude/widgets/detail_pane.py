"""Context-sensitive detail pane (right side) that updates based on active panel selection."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import ContentSwitcher, Markdown, Static, TextArea, Tree
from textual.widgets.tree import TreeNode


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


class DetailPane(Widget):
    """Right-side detail view that switches content based on active panel selection."""

    BINDINGS = [
        Binding("escape", "cancel_edit", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    DetailPane {
        height: 1fr;
        width: 1fr;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._editing = False
        self._edit_callback: object = None

    def compose(self) -> ComposeResult:
        with ContentSwitcher(initial="detail-markdown"):
            yield Markdown(
                "*Select an item to view details*",
                id="detail-markdown",
            )
            yield Tree("settings", id="detail-tree")
            yield VerticalScroll(
                Static("", id="detail-text-content", markup=True),
                id="detail-text",
            )

    def show_markdown(self, title: str, content: str) -> None:
        if self._editing:
            return
        self.border_title = title
        try:
            self.query_one(ContentSwitcher).current = "detail-markdown"
            self.query_one("#detail-markdown", Markdown).update(
                content or "*No content*"
            )
        except Exception:
            pass

    def show_tree(self, title: str, data: dict) -> None:
        if self._editing:
            return
        self.border_title = title
        try:
            self.query_one(ContentSwitcher).current = "detail-tree"
            tree = self.query_one("#detail-tree", Tree)
            tree.clear()
            if data:
                _populate_tree(tree.root, data)
                tree.root.expand()
        except Exception:
            pass

    def show_text(self, title: str, text: str) -> None:
        if self._editing:
            return
        self.border_title = title
        try:
            self.query_one(ContentSwitcher).current = "detail-text"
            self.query_one("#detail-text-content", Static).update(text or "*No content*")
        except Exception:
            pass

    def start_edit(self, content: str, title: str = "Editing") -> None:
        self._editing = True
        self.border_title = f"{title} [dim](Ctrl+S save, Esc cancel)[/dim]"
        try:
            switcher = self.query_one(ContentSwitcher)
            editor = TextArea(content, id="detail-editor", language="markdown")
            switcher.mount(editor)
            switcher.current = "detail-editor"
            editor.focus()
        except Exception:
            self._editing = False

    def get_edit_text(self) -> str | None:
        if not self._editing:
            return None
        try:
            return self.query_one("#detail-editor", TextArea).text
        except Exception:
            return None

    def end_edit(self) -> None:
        self._editing = False
        try:
            self.query_one("#detail-editor", TextArea).remove()
        except Exception:
            pass
        try:
            self.query_one(ContentSwitcher).current = "detail-markdown"
        except Exception:
            pass

    def action_cancel_edit(self) -> None:
        if self._editing:
            self.end_edit()
            self.app.notify("Edit cancelled", timeout=2)

    @property
    def is_editing(self) -> bool:
        return self._editing
