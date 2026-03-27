# LazyClaude — Project Instructions

## What This Is
LazyGit-inspired TUI for managing the `~/.claude/` directory ecosystem. Built with Python 3.12+ and Textual 6.5.0.

## Tech Stack
- **Language**: Python 3.13
- **TUI Framework**: Textual 6.5.0 (Rich-based, CSS-like styling)
- **YAML**: PyYAML 6.0.2 for frontmatter parsing
- **Package**: `pyproject.toml` with hatchling, installable via `pip install -e .`
- **Entry point**: `lazyclaude` CLI or `python -m lazyclaude`

## Architecture
- `app.py` — Main `LazyClaude(App)` class: layout, bindings, event routing, panel-to-detail wiring
- `claude_dir.py` — `ClaudeDir` class: all filesystem I/O against `~/.claude/`. Backup-before-write.
- `models.py` — Dataclasses: `Project`, `MemoryFile`, `Skill`, `Agent`, `HistoryEntry`, `TranscriptSession`, `SessionMeta`, `ClaudeSettings`
- `history.py` — JSONL tail-reader for `history.jsonl` and session metadata parser
- `theme.py` — OLED TCSS theme as a string constant (`OLED_THEME`)
- `widgets/panel_widget.py` — Base `PanelWidget` + 6 concrete panels (Project, Config, Memory, Skill, Agent, Session)
- `widgets/detail_pane.py` — Right-side `DetailPane` with `ContentSwitcher` (Markdown/Tree/Text views)
- `widgets/memory_browser.py` — `ConfirmModal` and `NewMemoryModal` modal screens
- `widgets/help_overlay.py` — `?` keybinding reference

## Layout Pattern
Left: 6 vertically stacked `PanelWidget` subclasses with expand/collapse via CSS class toggling (`panel-expanded`). Right: single `DetailPane` that updates based on active panel's highlighted item.

## Key Patterns
- **Panel focus**: `on_descendant_focus` detects which panel is active, toggles CSS classes
- **Debounced highlights**: 120ms timer before detail pane renders (avoids Markdown re-render on every j/k)
- **Lazy content loading**: Agent/skill bodies loaded on first highlight, not at startup
- **CLAUDE.md cache**: Per-project cache, cleared on Ctrl+R reload
- **Message passing**: Panels post `ItemHighlighted`/`ItemSelected` messages, App handles routing
- **Write safety**: `ClaudeDir._backup()` copies to `~/.claude/backups/lazyclaude/` before any overwrite

## Conventions
- Commit messages: `type(scope): description` (e.g., `feat(sessions): add delete action`)
- CSS: Inline via `App.CSS` class variable from `theme.py`, not external `.tcss` files
- Panel widgets: Always subclass `PanelWidget`, define `panel_index`, `panel_label`, optional `subtabs`
- Data flow: `ClaudeDir` -> models -> panel widgets -> detail pane (never skip the data layer)

## Anti-Patterns
1. Don't call `Markdown.update()` on every j/k keystroke — always debounce
2. Don't load agent/skill content at startup — lazy-load on first view
3. Don't fall back to global CLAUDE.md when a project has none — show "none" explicitly
4. Don't use full-screen modals for confirmations — use compact y/n popups
5. Don't count history.jsonl entries as "sessions" — count actual `.jsonl` transcript files

## GitHub
- Repo: https://github.com/pibytectl/lazyclaude
- Branch: main
- Public repo
