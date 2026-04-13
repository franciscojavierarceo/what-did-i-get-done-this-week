"""
Native desktop popup interface with multiple fallback options
"""

import html
import json
import threading
import time
from pathlib import Path
from typing import Optional, Dict

import markdown as md

from rich.console import Console

console = Console()

# Import all available popup implementations
try:
    from .tkinter_popup import ModernTkinterPopup, modern_tkinter_available
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

try:
    import webview
    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False

try:
    from .applescript_popup import AppleScriptPopup, applescript_available
    APPLESCRIPT_AVAILABLE = True
except ImportError:
    APPLESCRIPT_AVAILABLE = False


class NativeReportPopup:
    """Native desktop popup for displaying reports and collecting reflections"""

    def __init__(self, report_content: str, report_path: str):
        self.report_content = report_content
        self.report_path = Path(report_path)
        self.reflection_questions = [
            ("What could I have done better?", "What could I have done better?"),
            ("What is important that I am missing?", "What is important that I am missing?"),
            ("Am I doing work that is aligned with my goals?", "Am I doing work that is aligned with my goals?"),
            ("How do I feel?", "How do I feel?"),
        ]
        self.result = None
        self.reflection_answers = {}

    def show(self, timeout_seconds: int = 300) -> Optional[str]:
        """Display native popup and wait for user interaction"""
        if not WEBVIEW_AVAILABLE:
            console.print("❌ webview library not available. Please install: pip install pywebview", style="yellow")
            return None

        try:
            # Create the HTML content
            html_content = self._generate_html()

            # Create JavaScript API for communication
            api = self._create_api()

            # Create the webview window
            console.print("🖥️ Opening native desktop popup...")

            window = webview.create_window(
                title='Reflection Time - What Did I Get Done?',
                html=html_content,
                width=1200,
                height=800,
                min_size=(800, 600),
                resizable=True,
                shadow=True,
                on_top=True,
                js_api=api
            )

            # Use a threading.Event so the timeout thread can be cancelled
            # immediately when the window closes normally (no leaked sleepers)
            self._done = threading.Event()

            def _on_closed():
                if not self.result:
                    self.result = "cancelled"
                self._done.set()

            window.events.closed += _on_closed

            # Schedule a timeout that destroys the window from inside the
            # webview event loop (safe on macOS). The func= callback runs
            # in the webview thread after the event loop starts.
            def _timeout_watchdog():
                if self._done.wait(timeout=timeout_seconds):
                    return  # window closed normally, nothing to do
                # Timed out — close the window
                console.print("⏰ Native popup session timed out", style="yellow")
                self.result = "timeout"
                try:
                    for w in webview.windows:
                        w.destroy()
                except Exception:
                    pass

            timer = threading.Thread(target=_timeout_watchdog, daemon=True)
            timer.start()

            # webview.start() must run on the main thread (macOS requirement).
            # It blocks until all windows are closed.
            webview.start(debug=False)

            # Ensure the timeout thread is cancelled
            self._done.set()

            return self.result

        except Exception as e:
            console.print(f"❌ Native popup failed: {e}", style="red")
            return None

    def _schedule_destroy(self):
        """Schedule window destruction from a background thread.

        On macOS, window.destroy() must be dispatched to the main thread.
        Calling it directly from a pywebview JS API callback deadlocks
        because the callback thread holds a lock the main thread needs.
        Using a short-lived timer thread avoids this.
        """
        def _do_destroy():
            time.sleep(0.1)  # let the JS callback return first
            try:
                if webview.windows:
                    webview.windows[0].destroy()
            except Exception as e:
                console.print(f"⚠️ Window cleanup: {e}", style="dim")

        threading.Thread(target=_do_destroy, daemon=True).start()

    def _create_api(self):
        """Create JavaScript API for window communication"""
        class API:
            def __init__(self, parent):
                self.parent = parent

            def save_reflections(self, answers):
                """Save reflections from JavaScript"""
                try:
                    if isinstance(answers, str):
                        answers = json.loads(answers)

                    self.parent.reflection_answers = answers
                    self.parent._save_reflections(answers)
                    self.parent.result = "saved"
                    self.parent._schedule_destroy()
                    return {"status": "success", "message": "Reflections saved successfully!"}

                except Exception as e:
                    return {"status": "error", "message": str(e)}

            def skip_reflections(self):
                """Skip reflections"""
                self.parent.result = "skipped"
                self.parent._schedule_destroy()
                return {"status": "success", "message": "Reflections skipped"}

            def disable_scheduling(self):
                """Disable scheduling"""
                self.parent.result = "disable"
                self.parent._schedule_destroy()
                return {"status": "success", "message": "Scheduling disabled"}

            def close_window(self):
                """Close the window"""
                if not self.parent.result:
                    self.parent.result = "cancelled"
                self.parent._schedule_destroy()
                return {"status": "success"}

        return API(self)

    def _extract_headers(self, markdown_text: str) -> list:
        """Extract h2/h3 headers from markdown for sidebar navigation"""
        import re
        headers = []
        for line in markdown_text.split('\n'):
            m = re.match(r'^(#{2,3})\s+(.+)', line)
            if m:
                level = len(m.group(1))
                text = m.group(2).strip()
                slug = re.sub(r'[^\w\s-]', '', text).strip().lower()
                slug = re.sub(r'[\s]+', '-', slug)
                headers.append((level, text, slug))
        return headers

    def _generate_html(self) -> str:
        """Generate the HTML interface"""
        # Generate reflection form
        reflection_form = ""
        for i, (question, _) in enumerate(self.reflection_questions):
            field_name = f"reflection_{question.lower().replace(' ', '_').replace('?', '')}"
            reflection_form += f'''
            <div class="reflection-item">
                <label for="{field_name}">{html.escape(question)}</label>
                <textarea
                    id="{field_name}"
                    name="{field_name}"
                    placeholder="Share your thoughts here..."
                    rows="3"
                ></textarea>
            </div>
            '''

        # Strip reflection sections from the report display — only show
        # reflections when they contain real user-written content.
        import re as _re_strip
        display_content = self.report_content
        reflection_match = _re_strip.search(r'^## [^\n]*Reflection', display_content, _re_strip.MULTILINE)
        if reflection_match:
            before = display_content[:reflection_match.start()].rstrip()
            section = display_content[reflection_match.start():]
            # Check if any line is real user content (not headings, placeholders, or boilerplate)
            has_real_content = any(
                line.strip() and
                not line.startswith('#') and
                not line.startswith('---') and
                not line.startswith('*[') and
                not line.startswith('*This report was') and
                line.strip() != '*'
                for line in section.split('\n')
            )
            if not has_real_content:
                display_content = before
            else:
                # Keep only the first reflection section with its content,
                # strip any duplicate reflection section
                parts = _re_strip.split(r'(?=^## [^\n]*Reflection)', section, flags=_re_strip.MULTILINE)
                # parts[0] is empty (split at start), parts[1:] are the sections
                kept_sections = []
                for part in parts:
                    if not part.strip():
                        continue
                    part_has_content = any(
                        line.strip() and
                        not line.startswith('#') and
                        not line.startswith('---') and
                        not line.startswith('*[') and
                        not line.startswith('*This report was') and
                        line.strip() != '*'
                        for line in part.split('\n')
                    )
                    if part_has_content:
                        kept_sections.append(part.rstrip())
                if kept_sections:
                    display_content = before + '\n\n' + '\n\n'.join(kept_sections)
                else:
                    display_content = before
        # Also strip the auto-generated footer
        display_content = _re_strip.sub(
            r'\n*\*This report was generated automatically[^\n]*\n*', '', display_content
        ).rstrip()

        # Extract headers for sidebar navigation
        headers = self._extract_headers(display_content)

        # Build sidebar nav items from headers
        sidebar_nav = ""
        for level, text, slug in headers:
            indent = "padding-left: 28px;" if level == 3 else ""
            font = "font-size: 12px;" if level == 3 else "font-size: 13px; font-weight: 600;"
            sidebar_nav += f'''<a class="sidebar-link" href="#section-{slug}" style="{indent} {font}">{html.escape(text)}</a>\n'''

        # Convert markdown to HTML, adding id anchors to headers
        import re as _re

        def _slugify(value, separator):
            s = _re.sub(r'[^\w\s-]', '', value).strip().lower()
            return 'section-' + _re.sub(r'[\s]+', '-', s)

        rendered_report = md.markdown(
            display_content,
            extensions=['tables', 'fenced_code', 'nl2br', 'toc'],
            extension_configs={
                'toc': {
                    'anchorlink': False,
                    'permalink': False,
                    'slugify': _slugify,
                }
            },
        )

        return f'''
        <!DOCTYPE html>
        <html data-theme="dark">
        <head>
            <title>Reflection Time</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                /* ── NIGHTBRIGHT: dark mode ── */
                :root[data-theme="dark"] {{
                    --bg:             #0a0a0a;
                    --bg-panel:       #0f0f0f;
                    --bg-line:        #141414;
                    --bg-elevated:    #1a1a1a;
                    --fg:             #b0b0b0;
                    --fg-muted:       #555;
                    --fg-heading:     #e0e0e0;
                    --accent:         #00ff41;
                    --accent-dim:     rgba(0,255,65,0.08);
                    --accent-glow:    rgba(0,255,65,0.25);
                    --blue:           #00d4ff;
                    --green:          #00ff41;
                    --orange:         #ffb020;
                    --red:            #ff3333;
                    --purple:         #bf7fff;
                    --cyan:           #00ffcc;
                    --border:         #1e1e1e;
                    --border-active:  #333;
                    --selection:      #003322;
                    --code-bg:        #050505;
                    --btn-primary:    #00ff41;
                    --btn-primary-fg: #0a0a0a;
                    --btn-secondary:  #333;
                    --btn-secondary-fg: #b0b0b0;
                    --btn-danger:     #ff3333;
                    --btn-danger-fg:  #0a0a0a;
                    --success:        #00ff41;
                    --tab-active-border: #00ff41;
                    --font-mono:      'SF Mono', 'Fira Code', 'JetBrains Mono', Monaco, Consolas, 'Courier New', monospace;
                    --scanline:       rgba(0,255,65,0.015);
                }}

                /* ── NIGHTBRIGHT: light mode ── */
                :root[data-theme="light"] {{
                    --bg:             #f5f5f0;
                    --bg-panel:       #eaeae5;
                    --bg-line:        #e0e0db;
                    --bg-elevated:    #ddddd8;
                    --fg:             #333;
                    --fg-muted:       #888;
                    --fg-heading:     #111;
                    --accent:         #007a20;
                    --accent-dim:     rgba(0,122,32,0.08);
                    --accent-glow:    rgba(0,122,32,0.15);
                    --blue:           #0077cc;
                    --green:          #007a20;
                    --orange:         #cc7a00;
                    --red:            #cc2200;
                    --purple:         #7733aa;
                    --cyan:           #008866;
                    --border:         #ccc;
                    --border-active:  #aaa;
                    --selection:      #c8e8d0;
                    --code-bg:        #e0e0db;
                    --btn-primary:    #007a20;
                    --btn-primary-fg: #fff;
                    --btn-secondary:  #bbb;
                    --btn-secondary-fg: #333;
                    --btn-danger:     #cc2200;
                    --btn-danger-fg:  #fff;
                    --success:        #007a20;
                    --tab-active-border: #007a20;
                    --font-mono:      'SF Mono', 'Fira Code', 'JetBrains Mono', Monaco, Consolas, 'Courier New', monospace;
                    --scanline:       transparent;
                }}

                /* ── Reset ── */
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}

                body {{
                    font-family: var(--font-mono);
                    background: var(--bg);
                    color: var(--fg);
                    height: 100vh;
                    overflow: hidden;
                    font-size: 13px;
                }}

                /* ── Scanline overlay (dark mode only) ── */
                .app-container::before {{
                    content: '';
                    position: fixed;
                    top: 0; left: 0; right: 0; bottom: 0;
                    background: repeating-linear-gradient(
                        0deg,
                        var(--scanline) 0px,
                        var(--scanline) 1px,
                        transparent 1px,
                        transparent 3px
                    );
                    pointer-events: none;
                    z-index: 9999;
                }}

                /* ── Layout ── */
                .app-container {{
                    height: 100vh;
                    display: flex;
                    flex-direction: column;
                    position: relative;
                }}

                /* ── Top bar ── */
                .top-bar {{
                    display: flex;
                    align-items: stretch;
                    background: var(--bg-panel);
                    border-bottom: 1px solid var(--border);
                    min-height: 40px;
                }}

                .tabs {{
                    display: flex;
                    flex: 1;
                }}

                .tab {{
                    padding: 10px 24px;
                    border: none;
                    background: none;
                    color: var(--fg-muted);
                    font-size: 12px;
                    font-weight: 600;
                    font-family: var(--font-mono);
                    cursor: pointer;
                    border-bottom: 2px solid transparent;
                    transition: all 0.15s ease;
                    text-transform: uppercase;
                    letter-spacing: 0.1em;
                }}

                .tab:hover {{
                    color: var(--fg);
                    background: var(--bg-elevated);
                }}

                .tab.active {{
                    color: var(--accent);
                    border-bottom-color: var(--tab-active-border);
                    text-shadow: 0 0 8px var(--accent-glow);
                }}

                .theme-toggle {{
                    display: flex;
                    align-items: center;
                    padding: 0 16px;
                    border: none;
                    background: none;
                    color: var(--fg-muted);
                    font-size: 12px;
                    font-family: var(--font-mono);
                    font-weight: 600;
                    cursor: pointer;
                    transition: color 0.15s ease;
                    text-transform: uppercase;
                    letter-spacing: 0.1em;
                    gap: 6px;
                }}

                .theme-toggle:hover {{
                    color: var(--accent);
                    text-shadow: 0 0 8px var(--accent-glow);
                }}

                /* ── Content area ── */
                .content {{
                    flex: 1;
                    display: flex;
                    overflow: hidden;
                }}

                /* ── Sidebar ── */
                .sidebar {{
                    width: 220px;
                    background: var(--bg-panel);
                    border-right: 1px solid var(--border);
                    overflow-y: auto;
                    padding: 12px 0;
                    flex-shrink: 0;
                }}

                .sidebar-title {{
                    padding: 8px 16px;
                    font-size: 10px;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 0.15em;
                    color: var(--accent);
                    opacity: 0.6;
                }}

                .sidebar-link {{
                    display: block;
                    padding: 5px 16px;
                    color: var(--fg-muted);
                    text-decoration: none;
                    font-size: 12px;
                    border-left: 2px solid transparent;
                    transition: all 0.12s ease;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }}

                .sidebar-link:hover {{
                    color: var(--fg);
                    background: var(--bg-elevated);
                    border-left-color: var(--border-active);
                }}

                .sidebar-link.active {{
                    color: var(--accent);
                    border-left-color: var(--accent);
                    background: var(--accent-dim);
                    text-shadow: 0 0 6px var(--accent-glow);
                }}

                /* ── Main content ── */
                .main-content {{
                    flex: 1;
                    overflow-y: auto;
                    padding: 28px 32px;
                    scroll-behavior: smooth;
                }}

                .tab-content {{
                    display: none;
                }}

                .tab-content.active {{
                    display: block;
                }}

                /* ── Report markdown ── */
                .report-content {{
                    line-height: 1.7;
                    font-size: 13px;
                    max-width: 800px;
                }}

                .report-content h1 {{
                    font-size: 1.5em;
                    color: var(--accent);
                    margin: 0 0 20px 0;
                    padding-bottom: 8px;
                    border-bottom: 1px solid var(--border);
                    text-shadow: 0 0 10px var(--accent-glow);
                    font-weight: 700;
                }}

                .report-content h2 {{
                    font-size: 1.2em;
                    color: var(--accent);
                    margin: 28px 0 10px 0;
                    padding-bottom: 4px;
                    border-bottom: 1px solid var(--border);
                    opacity: 0.9;
                }}

                .report-content h3 {{
                    font-size: 1.05em;
                    color: var(--cyan);
                    margin: 20px 0 6px 0;
                }}

                .report-content ul, .report-content ol {{
                    margin: 6px 0 6px 20px;
                    padding: 0;
                }}

                .report-content li {{
                    margin-bottom: 3px;
                }}

                .report-content li::marker {{
                    color: var(--accent);
                }}

                .report-content p {{
                    margin: 6px 0;
                }}

                .report-content strong {{
                    color: var(--fg-heading);
                    font-weight: 700;
                }}

                .report-content em {{
                    color: var(--cyan);
                    font-style: italic;
                }}

                .report-content code {{
                    background: var(--code-bg);
                    padding: 1px 5px;
                    border-radius: 3px;
                    font-family: var(--font-mono);
                    font-size: 0.95em;
                    color: var(--green);
                    border: 1px solid var(--border);
                }}

                .report-content pre {{
                    background: var(--code-bg);
                    padding: 14px;
                    border-radius: 4px;
                    border: 1px solid var(--border);
                    overflow-x: auto;
                    margin: 10px 0;
                }}

                .report-content pre code {{
                    background: none;
                    padding: 0;
                    color: var(--fg);
                    border: none;
                }}

                .report-content table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 10px 0;
                    font-size: 12px;
                }}

                .report-content th, .report-content td {{
                    border: 1px solid var(--border);
                    padding: 6px 10px;
                    text-align: left;
                }}

                .report-content th {{
                    background: var(--bg-elevated);
                    font-weight: 700;
                    color: var(--accent);
                    text-transform: uppercase;
                    font-size: 11px;
                    letter-spacing: 0.05em;
                }}

                .report-content blockquote {{
                    border-left: 3px solid var(--accent);
                    margin: 10px 0;
                    padding: 6px 14px;
                    background: var(--bg-elevated);
                    border-radius: 0 4px 4px 0;
                    color: var(--fg-muted);
                    font-style: italic;
                }}

                .report-content a {{
                    color: var(--blue);
                    text-decoration: none;
                }}

                .report-content a:hover {{
                    text-decoration: underline;
                    text-shadow: 0 0 6px var(--blue);
                }}

                .report-content hr {{
                    border: none;
                    border-top: 1px solid var(--border);
                    margin: 20px 0;
                }}

                /* ── Reflections form ── */
                .reflection-item {{
                    margin-bottom: 22px;
                }}

                .reflection-item label {{
                    display: block;
                    font-weight: 700;
                    margin-bottom: 6px;
                    color: var(--accent);
                    font-size: 12px;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }}

                .reflection-item textarea {{
                    width: 100%;
                    padding: 10px;
                    border: 1px solid var(--border);
                    border-radius: 4px;
                    font-size: 13px;
                    font-family: var(--font-mono);
                    resize: vertical;
                    transition: border-color 0.15s ease, box-shadow 0.15s ease;
                    min-height: 72px;
                    background: var(--code-bg);
                    color: var(--fg);
                }}

                .reflection-item textarea:focus {{
                    outline: none;
                    border-color: var(--accent);
                    box-shadow: 0 0 0 2px var(--accent-dim), 0 0 12px var(--accent-glow);
                }}

                .reflection-item textarea::placeholder {{
                    color: var(--fg-muted);
                }}

                /* ── Footer ── */
                .footer {{
                    padding: 12px 24px;
                    background: var(--bg-panel);
                    border-top: 1px solid var(--border);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}

                .btn {{
                    padding: 8px 18px;
                    border: 1px solid var(--border);
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 700;
                    cursor: pointer;
                    transition: all 0.15s ease;
                    text-decoration: none;
                    display: inline-block;
                    font-family: var(--font-mono);
                    text-transform: uppercase;
                    letter-spacing: 0.06em;
                }}

                .btn:hover {{
                    transform: translateY(-1px);
                }}

                .btn-primary {{
                    background: var(--btn-primary);
                    color: var(--btn-primary-fg);
                    border-color: var(--btn-primary);
                }}

                .btn-primary:hover {{
                    box-shadow: 0 0 16px var(--accent-glow), 0 4px 12px rgba(0,0,0,0.4);
                }}

                .btn-secondary {{
                    background: var(--btn-secondary);
                    color: var(--btn-secondary-fg);
                    border-color: var(--border-active);
                    margin-left: 10px;
                }}

                .btn-secondary:hover {{
                    background: var(--bg-elevated);
                    color: var(--fg);
                }}

                .btn-danger {{
                    background: transparent;
                    color: var(--red);
                    border-color: var(--red);
                }}

                .btn-danger:hover {{
                    background: var(--red);
                    color: var(--btn-danger-fg);
                    box-shadow: 0 0 12px rgba(255,51,51,0.3);
                }}

                /* ── Toast ── */
                .success-message {{
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: var(--bg-panel);
                    color: var(--accent);
                    padding: 10px 16px;
                    border-radius: 4px;
                    border: 1px solid var(--accent);
                    font-weight: 700;
                    font-family: var(--font-mono);
                    font-size: 12px;
                    box-shadow: 0 0 20px var(--accent-glow);
                    z-index: 1000;
                    opacity: 0;
                    transform: translateX(100%);
                    transition: all 0.3s ease;
                }}

                .success-message.show {{
                    opacity: 1;
                    transform: translateX(0);
                }}

                /* ── Scrollbar ── */
                ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
                ::-webkit-scrollbar-track {{ background: var(--bg); }}
                ::-webkit-scrollbar-thumb {{ background: var(--border-active); border-radius: 3px; }}
                ::-webkit-scrollbar-thumb:hover {{ background: var(--accent); }}
            </style>
        </head>
        <body>
            <div class="app-container">
                <div class="top-bar">
                    <div class="tabs">
                        <button class="tab active" data-tab="report" onclick="showTab('report', this)">Report</button>
                        <button class="tab" data-tab="reflections" onclick="showTab('reflections', this)">Reflections</button>
                    </div>
                    <button class="theme-toggle" onclick="toggleTheme()" title="Toggle light/dark mode" id="themeBtn">
                        <span id="themeIcon">&#9789;</span> <span id="themeLabel">LIGHT</span>
                    </button>
                </div>

                <div class="content">
                    <div class="sidebar" id="sidebar">
                        <div class="sidebar-title">On this page</div>
                        {sidebar_nav}
                    </div>

                    <div class="main-content" id="mainContent">
                        <div class="tab-content active" id="report">
                            <div class="report-content">{rendered_report}</div>
                        </div>

                        <div class="tab-content" id="reflections">
                            <form id="reflectionForm" style="max-width: 700px;">
                                {reflection_form}
                            </form>
                        </div>
                    </div>
                </div>

                <div class="footer">
                    <div>
                        <button type="button" class="btn btn-primary" onclick="saveReflections()">
                            Save Reflections &amp; Close
                        </button>
                        <button type="button" class="btn btn-secondary" onclick="skipReflections()">
                            Skip
                        </button>
                    </div>
                    <button type="button" class="btn btn-danger" onclick="disableScheduling()">
                        Disable Scheduling
                    </button>
                </div>
            </div>

            <div class="success-message" id="successMessage">
                <span id="successText">Done!</span>
            </div>

            <script>
                /* ── Theme ── */
                function toggleTheme() {{
                    const html = document.documentElement;
                    const current = html.getAttribute('data-theme');
                    const next = current === 'dark' ? 'light' : 'dark';
                    html.setAttribute('data-theme', next);
                    document.getElementById('themeIcon').innerHTML = next === 'dark' ? '&#9789;' : '&#9788;';
                    document.getElementById('themeLabel').textContent = next === 'dark' ? 'LIGHT' : 'DARK';
                }}

                /* ── Tabs ── */
                function showTab(tabName, btn) {{
                    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    document.getElementById(tabName).classList.add('active');
                    if (btn) btn.classList.add('active');

                    // Show sidebar only on report tab
                    const sidebar = document.getElementById('sidebar');
                    sidebar.style.display = tabName === 'report' ? '' : 'none';
                }}

                /* ── Sidebar scroll-spy ── */
                const mainContent = document.getElementById('mainContent');
                const sidebarLinks = document.querySelectorAll('.sidebar-link');

                function updateActiveSidebarLink() {{
                    const scrollTop = mainContent.scrollTop;
                    let currentId = '';

                    document.querySelectorAll('.report-content h2[id], .report-content h3[id]').forEach(heading => {{
                        if (heading.offsetTop - 80 <= scrollTop) {{
                            currentId = heading.id;
                        }}
                    }});

                    sidebarLinks.forEach(link => {{
                        const href = link.getAttribute('href');
                        if (href === '#' + currentId) {{
                            link.classList.add('active');
                        }} else {{
                            link.classList.remove('active');
                        }}
                    }});
                }}

                mainContent.addEventListener('scroll', updateActiveSidebarLink);

                // Smooth scroll on sidebar click
                sidebarLinks.forEach(link => {{
                    link.addEventListener('click', function(e) {{
                        e.preventDefault();
                        const targetId = this.getAttribute('href').substring(1);
                        const target = document.getElementById(targetId);
                        if (target) {{
                            mainContent.scrollTo({{ top: target.offsetTop - 20, behavior: 'smooth' }});
                        }}
                    }});
                }});

                /* ── Reflections API ── */
                function collectReflectionAnswers() {{
                    const answers = {{}};
                    document.querySelectorAll('#reflections textarea').forEach(textarea => {{
                        const questionKey = textarea.name.replace('reflection_', '').replace('_', ' ');
                        answers[questionKey] = textarea.value.trim();
                    }});
                    return answers;
                }}

                function showSuccessMessage(message) {{
                    const messageEl = document.getElementById('successMessage');
                    const textEl = document.getElementById('successText');
                    textEl.textContent = message;
                    messageEl.classList.add('show');
                    setTimeout(() => messageEl.classList.remove('show'), 3000);
                }}

                async function saveReflections() {{
                    try {{
                        const answers = collectReflectionAnswers();
                        const result = await pywebview.api.save_reflections(JSON.stringify(answers));
                        if (result.status === 'success') {{
                            showSuccessMessage('Reflections saved!');
                            // Python API handles window close via _schedule_destroy
                        }} else {{
                            alert('Error: ' + result.message);
                        }}
                    }} catch (error) {{
                        alert('Failed to save reflections: ' + error.message);
                    }}
                }}

                async function skipReflections() {{
                    try {{
                        await pywebview.api.skip_reflections();
                        // Python API handles window close
                    }} catch (error) {{
                        alert('Error: ' + error.message);
                    }}
                }}

                async function disableScheduling() {{
                    if (confirm('Are you sure you want to disable all scheduled reports?')) {{
                        try {{
                            await pywebview.api.disable_scheduling();
                            // Python API handles window close
                        }} catch (error) {{
                            alert('Error: ' + error.message);
                        }}
                    }}
                }}

                // Activate first sidebar link on load
                if (sidebarLinks.length > 0) sidebarLinks[0].classList.add('active');
            </script>
        </body>
        </html>
        '''

    def _save_reflections(self, answers: Dict[str, str]):
        """Save reflections to the markdown file"""
        import re as _re
        try:
            content = self.report_path.read_text()

            # Build reflection section
            reflection_lines = ["\n## 🤔 Reflections\n"]
            for question, header in self.reflection_questions:
                answer_key = question.lower().replace(' ', '_').replace('?', '')
                answer = answers.get(question, '') or answers.get(answer_key, '')
                answer = answer.strip()

                if answer:
                    reflection_lines.append(f"### {header}\n\n{answer}\n")
                else:
                    reflection_lines.append(f"### {header}\n\n*[Add your thoughts]*\n")

            reflection_section = "\n".join(reflection_lines)

            # Find the first reflection heading (handles both "🎯 Weekly/Daily Reflection"
            # from the formatter and "🤔 Reflections" from previous saves)
            match = _re.search(r'^## [^\n]*Reflection', content, _re.MULTILINE)
            if match:
                before = content[:match.start()].rstrip()
            else:
                before = content.rstrip()

            new_content = before + "\n" + reflection_section

            self.report_path.write_text(new_content)

        except Exception as e:
            console.print(f"❌ Failed to save reflections: {e}", style="red")
            raise


def show_native_popup(report_content: str, report_path: str, preferred_method: str = "auto") -> Optional[str]:
    """Show native popup using the best available method"""

    # Determine the best popup method
    if preferred_method == "tkinter" and TKINTER_AVAILABLE and modern_tkinter_available():
        popup = ModernTkinterPopup(report_content, report_path)
        return popup.show()
    elif preferred_method == "webview" and WEBVIEW_AVAILABLE:
        popup = NativeReportPopup(report_content, report_path)
        return popup.show()
    elif preferred_method == "applescript" and APPLESCRIPT_AVAILABLE and applescript_available():
        popup = AppleScriptPopup(report_content, report_path)
        return popup.show()
    elif preferred_method == "auto":
        # Auto-select best available option

        # Try webview first (renders HTML/markdown properly)
        if WEBVIEW_AVAILABLE:
            console.print("🖥️ Using webview interface...", style="green")
            popup = NativeReportPopup(report_content, report_path)
            return popup.show()

        # Fallback to tkinter (cannot render markdown, but functional)
        elif TKINTER_AVAILABLE and modern_tkinter_available():
            console.print("🖥️ Using tkinter interface...", style="yellow")
            popup = ModernTkinterPopup(report_content, report_path)
            return popup.show()

        # Last resort: AppleScript (functional but basic)
        elif APPLESCRIPT_AVAILABLE and applescript_available():
            console.print("🖥️ Using AppleScript interface...", style="yellow")
            popup = AppleScriptPopup(report_content, report_path)
            return popup.show()

        else:
            console.print("❌ No native popup interface available", style="red")
            return None

    else:
        console.print(f"❌ Requested popup method '{preferred_method}' not available", style="red")
        return None


def native_popup_available() -> bool:
    """Check if any native popup implementation is available"""
    return (
        (TKINTER_AVAILABLE and modern_tkinter_available()) or
        WEBVIEW_AVAILABLE or
        (APPLESCRIPT_AVAILABLE and applescript_available())
    )