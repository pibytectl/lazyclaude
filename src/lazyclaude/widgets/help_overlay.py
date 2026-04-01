from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import DataTable, Label, Static

KEYBINDINGS = [
    ("Navigation", "1-7", "Jump to panel"),
    ("Navigation", "j / k", "Move up / down"),
    ("Navigation", "l / h", "Focus detail / back to panel"),
    ("Navigation", "[ / ]", "Cycle sub-tabs"),
    ("Actions", "Enter", "Select / view / edit"),
    ("Actions", "d", "Delete (memory, session, project)"),
    ("Actions", "e", "Edit file (.md)"),
    ("Actions", "Ctrl+S / Esc", "Save / cancel edit"),
    ("App", "? / q / r", "Help / quit / reload"),
]


class HelpOverlay(ModalScreen):
    def compose(self) -> ComposeResult:
        with Static(id="help-dialog"):
            yield Label("LazyClaude — Keybindings  [dim](?)[/dim]", id="help-title")
            table = DataTable(id="help-table", show_cursor=False)
            table.add_columns("Context", "Key", "Action")
            for row in KEYBINDINGS:
                table.add_row(*row)
            yield table
            yield Label("\n[dim]Press ? to close • Footer shows context-sensitive keys[/dim]")

    BINDINGS = [
        Binding("question_mark", "dismiss", "Close", show=False),
    ]
