from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Button,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    Select,
    Static,
    TextArea,
)

from lazyclaude.claude_dir import ClaudeDir
from lazyclaude.models import MemoryFile, MemoryType, Project

TYPE_COLORS = {
    MemoryType.USER: "cyan",
    MemoryType.PROJECT: "red",
    MemoryType.FEEDBACK: "yellow",
    MemoryType.REFERENCE: "magenta",
    MemoryType.UNKNOWN: "white",
}

TYPE_OPTIONS = [
    ("user", MemoryType.USER),
    ("project", MemoryType.PROJECT),
    ("feedback", MemoryType.FEEDBACK),
    ("reference", MemoryType.REFERENCE),
]


class ConfirmModal(ModalScreen[bool]):
    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._message = message

    def compose(self) -> ComposeResult:
        with Static(id="confirm-dialog"):
            yield Label(self._message, id="confirm-message")
            with Static(id="confirm-buttons"):
                yield Button("Cancel [Esc]", id="btn-cancel")
                yield Button("Delete [y]", id="btn-confirm", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-confirm")

    def on_key(self, event) -> None:
        if event.key == "y":
            self.dismiss(True)
        elif event.key == "escape":
            self.dismiss(False)


class NewMemoryModal(ModalScreen[dict | None]):
    def compose(self) -> ComposeResult:
        with Static(id="new-memory-dialog"):
            yield Label("New Memory File", id="new-memory-title")
            yield Label("Filename (without .md)", classes="field-label")
            yield Input(placeholder="e.g. feedback_testing", id="input-filename")
            yield Label("Name", classes="field-label")
            yield Input(placeholder="e.g. Testing approach", id="input-name")
            yield Label("Description", classes="field-label")
            yield Input(placeholder="One-line description", id="input-description")
            yield Label("Type", classes="field-label")
            yield Select(
                [(t[0], t[1]) for t in TYPE_OPTIONS],
                id="select-type",
                value=MemoryType.PROJECT,
            )
            with Static(id="new-memory-buttons"):
                yield Button("Cancel [Esc]", id="btn-cancel")
                yield Button("Create [Enter]", id="btn-create", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-create":
            self._submit()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
        elif event.key == "ctrl+enter":
            self._submit()

    def _submit(self) -> None:
        filename = self.query_one("#input-filename", Input).value.strip()
        name = self.query_one("#input-name", Input).value.strip()
        description = self.query_one("#input-description", Input).value.strip()
        mem_type = self.query_one("#select-type", Select).value

        if not filename or not name:
            self.notify("Filename and name are required", severity="error")
            return

        self.dismiss({
            "filename": filename,
            "name": name,
            "description": description,
            "memory_type": mem_type,
        })


class MemoryBrowser(Widget):
    BINDINGS = [
        Binding("n", "new_memory", "New"),
        Binding("d", "delete_memory", "Delete"),
        Binding("escape", "cancel_edit", "Cancel", show=False),
    ]

    def __init__(self, claude_dir: ClaudeDir, **kwargs) -> None:
        super().__init__(**kwargs)
        self._claude_dir = claude_dir
        self._project: Project | None = None
        self._memory_files: list[MemoryFile] = []
        self._selected: MemoryFile | None = None
        self._editing = False

    def compose(self) -> ComposeResult:
        yield ListView(id="memory-list")
        yield Markdown("*Select a project to view memory files*", id="memory-preview")

    def on_mount(self) -> None:
        pass

    def load_project(self, project: Project) -> None:
        self._project = project
        self._editing = False
        self._selected = None
        self._memory_files = self._claude_dir.load_memory_files(project)
        self._render_list()
        self._render_preview(None)

    def _render_list(self) -> None:
        lv = self.query_one("#memory-list", ListView)
        lv.clear()
        if not self._memory_files:
            lv.append(ListItem(Static("[dim]No memory files[/dim]")))
            return
        for mem in self._memory_files:
            color = TYPE_COLORS.get(mem.memory_type, "white")
            label = f"[{color}]{mem.memory_type.value[:3].upper()}[/{color}] {mem.name}"
            item = ListItem(Static(label))
            item.data = mem  # type: ignore[attr-defined]
            lv.append(item)

    def _render_preview(self, mem: MemoryFile | None) -> None:
        preview = self.query_one("#memory-preview", Markdown)
        if mem is None:
            preview.update("*Select a memory file to preview*")
        else:
            preview.update(f"# {mem.name}\n\n{mem.description}\n\n---\n\n{mem.content}")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        mem: MemoryFile | None = getattr(item, "data", None)
        if mem is None:
            return
        self._selected = mem
        if self._editing:
            self._cancel_edit()
        self._render_preview(mem)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        item = event.item
        if item is None:
            return
        mem: MemoryFile | None = getattr(item, "data", None)
        if mem is not None:
            self._selected = mem
            self._render_preview(mem)

    def on_key(self, event) -> None:
        if event.key == "enter" and self._selected and not self._editing:
            self._start_edit()
            event.stop()
        elif event.key == "ctrl+s" and self._editing:
            self._save_edit()
            event.stop()

    def _start_edit(self) -> None:
        if self._selected is None:
            return
        self._editing = True
        preview = self.query_one("#memory-preview", Markdown)
        preview.display = False
        editor = TextArea(
            self._selected.content,
            id="memory-editor",
            language="markdown",
        )
        self.mount(editor)
        editor.focus()
        self.notify("Editing — Ctrl+S to save, Escape to cancel", timeout=3)

    def _save_edit(self) -> None:
        if self._selected is None:
            return
        editor = self.query("#memory-editor")
        if not editor:
            return
        text_area = editor.first(TextArea)
        self._selected.content = text_area.text
        self._claude_dir.save_memory_file(self._selected)
        text_area.remove()
        self._editing = False
        preview = self.query_one("#memory-preview", Markdown)
        preview.display = True
        self._render_preview(self._selected)
        self.notify("Memory file saved", severity="information", timeout=2)

    def _cancel_edit(self) -> None:
        editor = self.query("#memory-editor")
        if editor:
            editor.first(TextArea).remove()
        self._editing = False
        preview = self.query_one("#memory-preview", Markdown)
        preview.display = True

    def action_cancel_edit(self) -> None:
        if self._editing:
            self._cancel_edit()

    def action_new_memory(self) -> None:
        if self._project is None:
            self.notify("Select a project first", severity="warning")
            return

        def on_result(result: dict | None) -> None:
            if result is None:
                return
            mem = self._claude_dir.create_memory_file(
                project=self._project,  # type: ignore[arg-type]
                filename=result["filename"],
                name=result["name"],
                memory_type=result["memory_type"],
                description=result["description"],
            )
            self._memory_files = self._claude_dir.load_memory_files(self._project)  # type: ignore[arg-type]
            self._render_list()
            self._selected = mem
            self._render_preview(mem)
            self.notify(f"Created {mem.filename}", severity="information", timeout=2)

        self.app.push_screen(NewMemoryModal(), on_result)

    def action_delete_memory(self) -> None:
        if self._selected is None:
            self.notify("No memory file selected", severity="warning")
            return

        def on_confirm(confirmed: bool) -> None:
            if not confirmed or self._selected is None or self._project is None:
                return
            self._claude_dir.delete_memory_file(self._selected, self._project)
            self._memory_files = self._claude_dir.load_memory_files(self._project)
            self._selected = None
            self._render_list()
            self._render_preview(None)
            self.notify("Memory file deleted", severity="information", timeout=2)

        self.app.push_screen(
            ConfirmModal(f"Delete '{self._selected.name}'?"),
            on_confirm,
        )
