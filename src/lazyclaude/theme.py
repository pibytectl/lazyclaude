OLED_THEME = """
/* ── Base ─────────────────────────────────────────────────────── */
Screen {
    background: #000000;
    color: #e0e0e0;
}

/* ── Header / Footer ─────────────────────────────────────────── */
Header {
    background: #0a0a0a;
    color: #00d4aa;
    height: 1;
}

Footer {
    background: #0a0a0a;
    color: #555555;
    height: 1;
}

FooterKey {
    background: #0a0a0a;
    color: #555555;
}

FooterKey .footer-key--key {
    background: #1a1a1a;
    color: #00d4aa;
}

FooterKey .footer-key--description {
    color: #888888;
}

/* ── Main Layout ──────────────────────────────────────────────── */
#main-layout {
    height: 1fr;
}

#left-panels {
    width: 34;
    height: 1fr;
}

/* ── Panel Base (collapsed state) ─────────────────────────────── */
PanelWidget {
    border: round #333333;
    border-title-color: #555555;
    border-title-style: bold;
    height: 3;
    padding: 0;
    background: #000000;
}

/* ── Panel Expanded (active/focused) ──────────────────────────── */
PanelWidget.panel-expanded {
    height: 1fr;
    border: round #00d4aa;
    border-title-color: #00d4aa;
}

/* ── ListView inside panels ───────────────────────────────────── */
PanelWidget ListView {
    background: #000000;
    height: 1fr;
}

PanelWidget ListItem {
    padding: 0 1;
    background: #000000;
    color: #c0c0c0;
    height: 1;
}

PanelWidget ListItem:hover {
    background: #0d1a0d;
}

PanelWidget ListView:focus ListItem.--highlight {
    background: #0d2818;
    color: #00d4aa;
}

/* Dim highlight when panel not focused */
PanelWidget ListView ListItem.--highlight {
    background: #0a0a0a;
    color: #888888;
}

/* ── Detail Pane ──────────────────────────────────────────────── */
DetailPane {
    border: round #333333;
    border-title-color: #555555;
    border-title-style: bold;
    width: 1fr;
    height: 1fr;
    background: #000000;
    padding: 0;
}

DetailPane.detail-active {
    border: round #00d4aa;
    border-title-color: #00d4aa;
}

DetailPane ContentSwitcher {
    height: 1fr;
    background: #000000;
}

/* ── Markdown ─────────────────────────────────────────────────── */
Markdown {
    background: #000000;
    color: #e0e0e0;
    margin: 0 1;
}

MarkdownViewer {
    background: #000000;
}

MarkdownH1 {
    color: #00d4aa;
    background: #000000;
}

MarkdownH2 {
    color: #4ecdc4;
    background: #000000;
}

MarkdownH3 {
    color: #a29bfe;
    background: #000000;
}

MarkdownCode {
    background: #0a0a0a;
    color: #feca57;
}

MarkdownCodeBlock {
    background: #0a0a0a;
}

MarkdownBullet {
    color: #00d4aa;
}

MarkdownTable {
    background: #000000;
}

/* ── Tree widget ──────────────────────────────────────────────── */
Tree {
    background: #000000;
    color: #c0c0c0;
    height: 1fr;
    padding: 0 1;
}

Tree > .tree--cursor {
    background: #0d2818;
    color: #00d4aa;
}

Tree > .tree--highlight {
    background: #0a0a0a;
}

/* ── TextArea editor ──────────────────────────────────────────── */
TextArea {
    background: #050505;
    color: #e0e0e0;
    border: tall #1a1a1a;
    height: 1fr;
}

TextArea:focus {
    border: tall #00d4aa;
}

/* ── Static text view ─────────────────────────────────────────── */
#detail-text {
    background: #000000;
    height: 1fr;
    padding: 0 1;
}

#detail-text-content {
    background: #000000;
    color: #c0c0c0;
}

/* ── Input ────────────────────────────────────────────────────── */
Input {
    background: #050505;
    border: tall #1a1a1a;
    color: #e0e0e0;
}

Input:focus {
    border: tall #00d4aa;
}

Select {
    background: #050505;
    border: tall #1a1a1a;
    color: #e0e0e0;
}

/* ── Buttons ──────────────────────────────────────────────────── */
Button {
    background: #1a1a1a;
    color: #c0c0c0;
    border: tall #333333;
    margin: 0 1;
}

Button:hover {
    background: #0d2818;
    color: #00d4aa;
}

Button.-primary {
    background: #0d2818;
    color: #00d4aa;
    border: tall #00d4aa;
}

Button.-error {
    background: #2a0d0d;
    color: #ff6b6b;
    border: tall #ff6b6b;
}

/* ── Modals ───────────────────────────────────────────────────── */
NewMemoryModal {
    align: center middle;
}

#new-memory-dialog {
    background: #0a0a0a;
    border: round #00d4aa;
    width: 60;
    height: 22;
    padding: 1 2;
}

#new-memory-title {
    color: #00d4aa;
    text-style: bold;
    margin-bottom: 1;
}

.field-label {
    color: #555555;
    margin-top: 1;
}

#new-memory-buttons {
    margin-top: 1;
    align: right middle;
}

ConfirmModal {
    align: center middle;
}

#confirm-dialog {
    background: #0a0a0a;
    border: round #ff6b6b;
    width: 50;
    height: 10;
    padding: 1 2;
}

#confirm-message {
    color: #e0e0e0;
    margin-bottom: 1;
}

#confirm-buttons {
    align: right middle;
    margin-top: 1;
}

/* ── Help Overlay ─────────────────────────────────────────────── */
HelpOverlay {
    align: center middle;
}

#help-dialog {
    background: #0a0a0a;
    border: round #00d4aa;
    width: 72;
    height: 38;
    padding: 1 2;
}

#help-title {
    color: #00d4aa;
    text-style: bold;
    margin-bottom: 1;
}

DataTable {
    background: #0a0a0a;
    color: #c0c0c0;
}

DataTable > .datatable--header {
    background: #0d2818;
    color: #00d4aa;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #0d1a0d;
    color: #00d4aa;
}

/* ── Badge/Label Colors ───────────────────────────────────────── */
.badge-user { color: #4ecdc4; }
.badge-project { color: #ff6b6b; }
.badge-feedback { color: #feca57; }
.badge-reference { color: #a29bfe; }
.badge-unknown { color: #555555; }
.label-muted { color: #555555; }
.label-accent { color: #00d4aa; }
"""
