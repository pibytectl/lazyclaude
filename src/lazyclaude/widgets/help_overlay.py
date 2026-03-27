from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import DataTable, Label, Static

KEYBINDINGS = [
    ("Global", "1-6", "Jump to panel"),
    ("Global", "Tab / Shift+Tab", "Cycle panel focus"),
    ("Global", "[ / ]", "Cycle sub-tabs within panel"),
    ("Global", "?", "Toggle this help"),
    ("Global", "q", "Quit"),
    ("Global", "Ctrl+R", "Reload all data"),
    ("Global", "Ctrl+S", "Save (when editing)"),
    ("Projects", "j / k", "Navigate"),
    ("Projects", "Enter", "Select project → loads Memory"),
    ("Config", "Enter", "View file in detail"),
    ("Config", "e", "Edit CLAUDE.md"),
    ("Memory", "j / k", "Navigate files"),
    ("Memory", "Enter", "Edit file"),
    ("Memory", "n", "New memory file"),
    ("Memory", "d", "Delete file"),
    ("Skills", "Enter", "View SKILL.md"),
    ("Skills", "[ / ]", "All / Active"),
    ("Agents", "Enter", "View agent prompt"),
    ("Agents", "[ / ]", "All / By Model"),
    ("Sessions", "Enter", "View entry"),
    ("Sessions", "[ / ]", "Recent / By Project"),
    ("Detail", "Escape", "Cancel edit"),
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
            yield Label("\n[dim]Press ? or Escape to close • Footer shows context-sensitive keys[/dim]")

    def on_key(self, event) -> None:
        if event.key in ("escape", "question_mark"):
            self.dismiss()
