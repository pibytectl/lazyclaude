from datetime import datetime

from textual.message import Message
from textual.widgets import ListItem, ListView, Static

from lazyclaude.models import Project


def _fmt_date(dt: datetime | None) -> str:
    if dt is None:
        return "never"
    now = datetime.now()
    delta = now - dt
    if delta.days == 0:
        return "today"
    if delta.days == 1:
        return "yesterday"
    if delta.days < 7:
        return f"{delta.days}d ago"
    if delta.days < 30:
        return f"{delta.days // 7}w ago"
    return dt.strftime("%b %d")


class ProjectList(ListView):
    class ProjectSelected(Message):
        def __init__(self, project: Project) -> None:
            super().__init__()
            self.project = project

    def __init__(self, projects: list[Project], **kwargs) -> None:
        super().__init__(**kwargs)
        self._projects = projects

    def on_mount(self) -> None:
        self._render_projects()

    def _render_projects(self) -> None:
        self.clear()
        for project in self._projects:
            label = self._make_label(project)
            item = ListItem(Static(label))
            item.data = project  # type: ignore[attr-defined]
            self.append(item)

    def _make_label(self, project: Project) -> str:
        name = project.short_name
        if project.display_name in ("/home/andy", "/home/andy/"):
            name = "~ (Global)"
        date = _fmt_date(project.last_active)
        mem_count = len(project.memory_files) if project.memory_files else 0
        # Truncate name to fit sidebar width
        max_name = 18
        if len(name) > max_name:
            name = name[: max_name - 1] + "…"
        return f"{name}\n[dim]{date}  {project.transcript_count}t  {mem_count}m[/dim]"

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        project: Project | None = getattr(item, "data", None)
        if project is not None:
            self.post_message(self.ProjectSelected(project))

    def refresh_projects(self, projects: list[Project]) -> None:
        self._projects = projects
        self._render_projects()
