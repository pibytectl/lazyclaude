OLED_THEME = """
/* ─────────────────────────────────────────────────────────────────
   LazyClaude OLED Theme

   Design: True black (#000000) background for pixel-off power savings.
   High-contrast selections using reverse-video and solid color bars.
   Accent: #00d4aa (teal-green) for active elements.
   ───────────────────────────────────────────────────────────────── */

/* ── Base ─────────────────────────────────────────────────────── */
Screen {
    background: #000000;
    color: #999999;
    scrollbar-color: #00d4aa;
    scrollbar-background: #0a0a0a;
    scrollbar-color-hover: #00ffcc;
    scrollbar-color-active: #00ffcc;
}

/* ── Header / Footer ─────────────────────────────────────────── */
Header {
    background: #000000;
    color: #00d4aa;
    height: 1;
}

Footer {
    background: #111111;
    height: 1;
}

FooterKey {
    background: #111111;
    color: #666666;
}

FooterKey .footer-key--key {
    background: #222222;
    color: #00d4aa;
}

FooterKey .footer-key--description {
    color: #999999;
}

/* ── Main Layout ──────────────────────────────────────────────── */
#main-layout {
    height: 1fr;
}

#left-panels {
    width: 42;
    height: 1fr;
}

/* ── Panel Base (collapsed state) ─────────────────────────────── */
PanelWidget {
    border: round #2a2a2a;
    border-title-color: #666666;
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
    color: #888888;
    height: 1;
}

PanelWidget ListItem:hover {
    background: #111111;
}

/* ── SELECTION — focused panel: solid teal bar, high contrast ── */
PanelWidget ListView:focus ListItem.--highlight {
    background: #00ff00;
    color: #000000;
    text-style: bold;
}

/* ── SELECTION — unfocused panel: dim but still visible ───────── */
PanelWidget ListView ListItem.--highlight {
    background: #1a1a1a;
    color: #00d4aa;
}

/* ── Detail Pane ──────────────────────────────────────────────── */
DetailPane {
    border: round #2a2a2a;
    border-title-color: #666666;
    border-title-style: bold;
    width: 1fr;
    height: 1fr;
    background: #000000;
    padding: 0;
}

DetailPane ContentSwitcher {
    height: 1fr;
    background: #000000;
}

/* ── Markdown ─────────────────────────────────────────────────── */
Markdown {
    background: #000000;
    color: #999999;
    margin: 0 1;
}

MarkdownViewer {
    background: #000000;
}

MarkdownH1 {
    color: #00d4aa;
    background: #000000;
    text-style: bold;
}

MarkdownH2 {
    color: #4ecdc4;
    background: #000000;
    text-style: bold;
}

MarkdownH3 {
    color: #a29bfe;
    background: #000000;
}

MarkdownCode {
    background: #111111;
    color: #feca57;
}

MarkdownCodeBlock {
    background: #0a0a0a;
}

MarkdownBullet {
    color: #00d4aa;
}

MarkdownBulletList {
    background: #000000;
}

MarkdownOrderedList {
    background: #000000;
}

MarkdownTable {
    background: #000000;
}

MarkdownBlockQuote {
    background: #0a0a0a;
    border-left: outer #00d4aa;
}

MarkdownHorizontalRule {
    color: #2a2a2a;
}

MarkdownFence {
    background: #0a0a0a;
}

/* ── Tree widget ──────────────────────────────────────────────── */
Tree {
    background: #000000;
    color: #aaaaaa;
    height: 1fr;
    padding: 0 1;
}

Tree:focus > .tree--cursor {
    background: #00d4aa;
    color: #000000;
    text-style: bold;
}

Tree > .tree--cursor {
    background: #1a1a1a;
    color: #00d4aa;
}

Tree > .tree--highlight {
    background: #111111;
}

Tree > .tree--guides {
    color: #2a2a2a;
}

/* ── TextArea editor ──────────────────────────────────────────── */
TextArea {
    background: #050505;
    color: #d0d0d0;
    border: tall #2a2a2a;
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
    color: #999999;
}

/* ── VerticalScroll ───────────────────────────────────────────── */
VerticalScroll {
    background: #000000;
}

VerticalScroll:focus {
    scrollbar-color: #00d4aa;
    scrollbar-color-hover: #00ffcc;
    scrollbar-color-active: #00ffcc;
}

/* ── Scrollbar ───────────────────────────────────────────────── */
Scrollbar {
    background: #0a0a0a;
    color: #333333;
}

DetailPane VerticalScroll:focus-within {
    border: round #00d4aa;
}

DetailPane Tree:focus {
    border: round #00d4aa;
}

/* ── Input ────────────────────────────────────────────────────── */
Input {
    background: #0a0a0a;
    border: tall #2a2a2a;
    color: #d0d0d0;
}

Input:focus {
    border: tall #00d4aa;
}

Select {
    background: #0a0a0a;
    border: tall #2a2a2a;
    color: #d0d0d0;
}

/* ── Buttons ──────────────────────────────────────────────────── */
Button {
    background: #1a1a1a;
    color: #aaaaaa;
    border: tall #333333;
    margin: 0 1;
}

Button:hover {
    background: #00d4aa;
    color: #000000;
}

Button.-primary {
    background: #00d4aa;
    color: #000000;
    border: tall #00d4aa;
    text-style: bold;
}

Button.-error {
    background: #ff4444;
    color: #000000;
    border: tall #ff4444;
    text-style: bold;
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
    color: #666666;
    margin-top: 1;
}

#new-memory-buttons {
    margin-top: 1;
    align: right middle;
}

ConfirmModal {
    align: center middle;
}

#confirm-popup {
    background: #111111;
    border: round #ff4444;
    color: #d0d0d0;
    width: auto;
    max-width: 60;
    height: auto;
    padding: 1 2;
    text-align: center;
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
    color: #aaaaaa;
}

DataTable > .datatable--header {
    background: #00d4aa;
    color: #000000;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #1a1a1a;
    color: #00d4aa;
}

/* ── Badge/Label Colors ───────────────────────────────────────── */
.badge-user { color: #4ecdc4; }
.badge-project { color: #ff6b6b; }
.badge-feedback { color: #feca57; }
.badge-reference { color: #a29bfe; }
.badge-unknown { color: #666666; }
.label-muted { color: #666666; }
.label-accent { color: #00d4aa; }
"""
