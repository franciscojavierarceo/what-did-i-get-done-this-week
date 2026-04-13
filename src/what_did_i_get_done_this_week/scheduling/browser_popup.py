"""
Browser-based popup interface for report display and reflection input
"""

import os
import tempfile
import webbrowser
import http.server
import socketserver
import threading
import time
import json
from pathlib import Path
from typing import Optional, Dict
from urllib.parse import urlparse, parse_qs

import markdown as md
from rich.console import Console

console = Console()


class ReflectionHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler for reflection form submission"""

    def __init__(self, *args, reflection_data=None, **kwargs):
        self.reflection_data = reflection_data
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html_content = self.reflection_data.get('html', '')
            self.wfile.write(html_content.encode())
        elif self.path.startswith('/submit'):
            # Parse form data from URL
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            # Extract reflection answers
            answers = {}
            for key, value in params.items():
                if key.startswith('reflection_'):
                    question_key = key.replace('reflection_', '').replace('_', ' ')
                    answers[question_key] = value[0] if value else ''

            # Store the result
            self.reflection_data['result'] = 'saved' if answers else 'skipped'
            self.reflection_data['answers'] = answers
            self.reflection_data['completed'] = True

            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            success_html = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Reflections Saved</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        text-align: center;
                        padding: 50px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        margin: 0;
                    }
                    .container {
                        background: rgba(255,255,255,0.1);
                        padding: 40px;
                        border-radius: 15px;
                        backdrop-filter: blur(10px);
                        display: inline-block;
                    }
                    h1 { margin: 0 0 20px 0; }
                    .emoji { font-size: 3em; margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="emoji">✅</div>
                    <h1>Reflections Saved!</h1>
                    <p>Your reflections have been saved to the markdown file.</p>
                    <p><em>You can close this tab now.</em></p>
                </div>
                <script>
                    setTimeout(function() { window.close(); }, 3000);
                </script>
            </body>
            </html>
            '''
            self.wfile.write(success_html.encode())

        else:
            self.send_error(404)

    def do_POST(self):
        """Handle POST requests for form submission"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')

        # Parse form data
        params = parse_qs(post_data)
        action = params.get('action', [''])[0]

        if action == 'save':
            # Extract reflection answers
            answers = {}
            for key, value in params.items():
                if key.startswith('reflection_'):
                    question_key = key.replace('reflection_', '').replace('_', ' ')
                    answers[question_key] = value[0] if value else ''

            self.reflection_data['result'] = 'saved'
            self.reflection_data['answers'] = answers
        elif action == 'skip':
            self.reflection_data['result'] = 'skipped'
            self.reflection_data['answers'] = {}
        elif action == 'disable':
            self.reflection_data['result'] = 'disable'
            self.reflection_data['answers'] = {}

        self.reflection_data['completed'] = True

        # Send success response (same as GET)
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        success_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Action Completed</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                .container {
                    background: rgba(255,255,255,0.1);
                    padding: 40px;
                    border-radius: 15px;
                    backdrop-filter: blur(10px);
                    display: inline-block;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div style="font-size: 3em; margin-bottom: 20px;">✅</div>
                <h1>Action Completed!</h1>
                <p>You can close this tab now.</p>
            </div>
            <script>
                setTimeout(function() { window.close(); }, 2000);
            </script>
        </body>
        </html>
        '''
        self.wfile.write(success_html.encode())

    def log_message(self, format, *args):
        """Suppress server logs"""
        pass


class BrowserReportPopup:
    """Browser-based popup for displaying reports and collecting reflections"""

    def __init__(self, report_content: str, report_path: str):
        self.report_content = report_content
        self.report_path = Path(report_path)
        self.reflection_questions = [
            ("What could I have done better?", "What could I have done better?"),
            ("What is important that I am missing?", "What is important that I am missing?"),
            ("Am I doing work that is aligned with my goals?", "Am I doing work that is aligned with my goals?"),
            ("How do I feel?", "How do I feel?"),
        ]
        self.server = None
        self.server_thread = None
        self.port = None

    def show(self) -> Optional[str]:
        """Display browser popup and wait for user interaction"""
        try:
            # Shared data for communication with the server
            reflection_data = {
                'html': self._generate_html(),
                'completed': False,
                'result': None,
                'answers': {}
            }

            # Start local server
            self.port = self._find_free_port()
            handler = lambda *args, **kwargs: ReflectionHandler(*args, reflection_data=reflection_data, **kwargs)

            self.server = socketserver.TCPServer(("localhost", self.port), handler)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()

            # Open browser in full-screen mode
            url = f"http://localhost:{self.port}"
            console.print(f"🌐 Opening full-screen reflection interface...")

            # Try to open in full-screen/kiosk mode if possible
            import platform
            import subprocess

            try:
                if platform.system() == 'Darwin':  # macOS
                    # Try to open with Chrome/Safari in full-screen mode
                    apps_to_try = [
                        ['open', '-a', 'Google Chrome', '--args', '--kiosk', url],
                        ['open', '-a', 'Safari', url],
                        ['open', url]  # Fallback to default browser
                    ]

                    opened = False
                    for app_cmd in apps_to_try:
                        try:
                            subprocess.run(app_cmd, check=True, capture_output=True)
                            opened = True
                            break
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            continue

                    if not opened:
                        webbrowser.open(url)

                elif platform.system() == 'Linux':
                    # Try with various Linux browsers in full-screen
                    browsers = [
                        ['google-chrome', '--kiosk', url],
                        ['chromium-browser', '--kiosk', url],
                        ['firefox', '--kiosk', url]
                    ]

                    opened = False
                    for browser_cmd in browsers:
                        try:
                            subprocess.Popen(browser_cmd)
                            opened = True
                            break
                        except FileNotFoundError:
                            continue

                    if not opened:
                        webbrowser.open(url)

                else:  # Windows or other
                    webbrowser.open(url)

            except Exception:
                # Fallback to regular browser opening
                webbrowser.open(url)

            # Wait for completion
            console.print("⏳ Waiting for you to complete the reflection form in your browser...")

            timeout = 300  # 5 minutes
            start_time = time.time()

            while not reflection_data['completed']:
                time.sleep(0.5)
                if time.time() - start_time > timeout:
                    console.print("⏰ Reflection session timed out", style="yellow")
                    return "timeout"

            # Process results
            if reflection_data['result'] == 'saved':
                self._save_reflections(reflection_data['answers'])

            return reflection_data['result']

        except Exception as e:
            console.print(f"❌ Browser popup failed: {e}", style="red")
            return None

        finally:
            if self.server:
                self.server.shutdown()
                self.server.server_close()

    def _find_free_port(self) -> int:
        """Find a free port for the local server"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

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
        import html as _html
        import re as _re

        # Strip reflection sections from the report display — only show
        # reflections when they contain real user-written content.
        display_content = self.report_content
        reflection_match = _re.search(r'^## [^\n]*Reflection', display_content, _re.MULTILINE)
        if reflection_match:
            before = display_content[:reflection_match.start()].rstrip()
            section = display_content[reflection_match.start():]
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
                parts = _re.split(r'(?=^## [^\n]*Reflection)', section, flags=_re.MULTILINE)
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
        display_content = _re.sub(
            r'\n*\*This report was generated automatically[^\n]*\n*', '', display_content
        ).rstrip()

        # Extract headers for sidebar navigation
        headers = self._extract_headers(display_content)

        sidebar_nav = ""
        for level, text, slug in headers:
            indent = "padding-left: 28px;" if level == 3 else ""
            font = "font-size: 12px;" if level == 3 else "font-size: 13px; font-weight: 600;"
            sidebar_nav += f'''<a class="sidebar-link" href="#section-{slug}" style="{indent} {font}">{_html.escape(text)}</a>\n'''

        # Convert markdown to HTML with toc for header IDs
        def _slugify(value, separator):
            s = _re.sub(r'[^\w\s-]', '', value).strip().lower()
            return 'section-' + _re.sub(r'[\s]+', '-', s)

        html_content = md.markdown(
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

        # Generate reflection form
        reflection_form = ""
        for i, (question, _) in enumerate(self.reflection_questions):
            field_name = f"reflection_{question.lower().replace(' ', '_').replace('?', '')}"
            reflection_form += f'''
            <div class="reflection-item">
                <label for="{field_name}">{_html.escape(question)}</label>
                <textarea
                    id="{field_name}"
                    name="{field_name}"
                    placeholder="Share your thoughts here..."
                    rows="3"
                ></textarea>
            </div>
            '''

        return f'''
        <!DOCTYPE html>
        <html data-theme="dark">
        <head>
            <title>Report &amp; Reflections</title>
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

                * {{ margin: 0; padding: 0; box-sizing: border-box; }}

                body {{
                    font-family: var(--font-mono);
                    background: var(--bg);
                    color: var(--fg);
                    min-height: 100vh;
                    margin: 0;
                    font-size: 13px;
                }}

                .app-container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    position: relative;
                }}

                .app-container::before {{
                    content: '';
                    position: fixed;
                    top: 0; left: 0; right: 0; bottom: 0;
                    background: repeating-linear-gradient(0deg, var(--scanline) 0px, var(--scanline) 1px, transparent 1px, transparent 3px);
                    pointer-events: none;
                    z-index: 9999;
                }}

                .top-bar {{
                    display: flex;
                    align-items: stretch;
                    background: var(--bg-panel);
                    border-bottom: 1px solid var(--border);
                    position: sticky;
                    top: 0;
                    z-index: 10;
                    min-height: 40px;
                }}

                .tabs {{ display: flex; flex: 1; }}

                .tab {{
                    padding: 10px 24px; border: none; background: none;
                    color: var(--fg-muted); font-size: 12px; font-weight: 600;
                    font-family: var(--font-mono); cursor: pointer;
                    border-bottom: 2px solid transparent;
                    transition: all 0.15s ease;
                    text-transform: uppercase; letter-spacing: 0.1em;
                }}

                .tab:hover {{ color: var(--fg); background: var(--bg-elevated); }}
                .tab.active {{ color: var(--accent); border-bottom-color: var(--tab-active-border); text-shadow: 0 0 8px var(--accent-glow); }}

                .theme-toggle {{
                    display: flex; align-items: center; padding: 0 16px;
                    border: none; background: none; color: var(--fg-muted);
                    font-size: 12px; font-family: var(--font-mono); font-weight: 600;
                    cursor: pointer; text-transform: uppercase; letter-spacing: 0.1em; gap: 6px;
                }}
                .theme-toggle:hover {{ color: var(--accent); text-shadow: 0 0 8px var(--accent-glow); }}

                .content {{ flex: 1; display: flex; overflow: hidden; }}

                .sidebar {{
                    width: 220px; background: var(--bg-panel);
                    border-right: 1px solid var(--border);
                    overflow-y: auto; padding: 12px 0; flex-shrink: 0;
                    position: sticky; top: 40px; max-height: calc(100vh - 40px - 52px);
                }}

                .sidebar-title {{
                    padding: 8px 16px; font-size: 10px; font-weight: 700;
                    text-transform: uppercase; letter-spacing: 0.15em;
                    color: var(--accent); opacity: 0.6;
                }}

                .sidebar-link {{
                    display: block; padding: 5px 16px; color: var(--fg-muted);
                    text-decoration: none; font-size: 12px;
                    border-left: 2px solid transparent;
                    transition: all 0.12s ease;
                    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
                }}

                .sidebar-link:hover {{ color: var(--fg); background: var(--bg-elevated); border-left-color: var(--border-active); }}
                .sidebar-link.active {{ color: var(--accent); border-left-color: var(--accent); background: var(--accent-dim); text-shadow: 0 0 6px var(--accent-glow); }}

                .main-content {{ flex: 1; overflow-y: auto; padding: 28px 32px; scroll-behavior: smooth; }}

                .tab-content {{ display: none; }}
                .tab-content.active {{ display: block; }}

                .report-content {{ line-height: 1.7; font-size: 13px; max-width: 800px; }}

                .report-content h1 {{ font-size: 1.5em; color: var(--accent); margin: 0 0 20px 0; padding-bottom: 8px; border-bottom: 1px solid var(--border); text-shadow: 0 0 10px var(--accent-glow); font-weight: 700; }}
                .report-content h2 {{ font-size: 1.2em; color: var(--accent); margin: 28px 0 10px 0; padding-bottom: 4px; border-bottom: 1px solid var(--border); opacity: 0.9; }}
                .report-content h3 {{ font-size: 1.05em; color: var(--cyan); margin: 20px 0 6px 0; }}
                .report-content ul, .report-content ol {{ margin: 6px 0 6px 20px; padding: 0; }}
                .report-content li {{ margin-bottom: 3px; }}
                .report-content li::marker {{ color: var(--accent); }}
                .report-content p {{ margin: 6px 0; }}
                .report-content strong {{ color: var(--fg-heading); font-weight: 700; }}
                .report-content em {{ color: var(--cyan); font-style: italic; }}
                .report-content code {{ background: var(--code-bg); padding: 1px 5px; border-radius: 3px; font-family: var(--font-mono); font-size: 0.95em; color: var(--green); border: 1px solid var(--border); }}
                .report-content pre {{ background: var(--code-bg); padding: 14px; border-radius: 4px; border: 1px solid var(--border); overflow-x: auto; margin: 10px 0; }}
                .report-content pre code {{ background: none; padding: 0; color: var(--fg); border: none; }}
                .report-content table {{ border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 12px; }}
                .report-content th, .report-content td {{ border: 1px solid var(--border); padding: 6px 10px; text-align: left; }}
                .report-content th {{ background: var(--bg-elevated); font-weight: 700; color: var(--accent); text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em; }}
                .report-content blockquote {{ border-left: 3px solid var(--accent); margin: 10px 0; padding: 6px 14px; background: var(--bg-elevated); border-radius: 0 4px 4px 0; color: var(--fg-muted); font-style: italic; }}
                .report-content a {{ color: var(--blue); text-decoration: none; }}
                .report-content a:hover {{ text-decoration: underline; text-shadow: 0 0 6px var(--blue); }}
                .report-content hr {{ border: none; border-top: 1px solid var(--border); margin: 20px 0; }}

                .reflection-item {{ margin-bottom: 22px; }}
                .reflection-item label {{ display: block; font-weight: 700; margin-bottom: 6px; color: var(--accent); font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; }}
                .reflection-item textarea {{
                    width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 4px;
                    font-size: 13px; font-family: var(--font-mono); resize: vertical; min-height: 72px;
                    background: var(--code-bg); color: var(--fg);
                    transition: border-color 0.15s ease, box-shadow 0.15s ease;
                }}
                .reflection-item textarea:focus {{ outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-dim), 0 0 12px var(--accent-glow); }}
                .reflection-item textarea::placeholder {{ color: var(--fg-muted); }}

                .footer {{
                    padding: 12px 24px; background: var(--bg-panel);
                    border-top: 1px solid var(--border);
                    display: flex; justify-content: space-between; align-items: center;
                }}

                .btn {{
                    padding: 8px 18px; border: 1px solid var(--border); border-radius: 4px;
                    font-size: 12px; font-weight: 700; cursor: pointer;
                    transition: all 0.15s ease; font-family: var(--font-mono);
                    text-transform: uppercase; letter-spacing: 0.06em;
                }}

                .btn:hover {{ transform: translateY(-1px); }}
                .btn-primary {{ background: var(--btn-primary); color: var(--btn-primary-fg); border-color: var(--btn-primary); }}
                .btn-primary:hover {{ box-shadow: 0 0 16px var(--accent-glow), 0 4px 12px rgba(0,0,0,0.4); }}
                .btn-secondary {{ background: var(--btn-secondary); color: var(--btn-secondary-fg); border-color: var(--border-active); margin-left: 10px; }}
                .btn-secondary:hover {{ background: var(--bg-elevated); color: var(--fg); }}
                .btn-danger {{ background: transparent; color: var(--red); border-color: var(--red); }}
                .btn-danger:hover {{ background: var(--red); color: var(--btn-danger-fg); box-shadow: 0 0 12px rgba(255,51,51,0.3); }}

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
                    <button class="theme-toggle" onclick="toggleTheme()" title="Toggle light/dark mode" id="themeBtn"><span id="themeIcon">&#9789;</span> <span id="themeLabel">LIGHT</span></button>
                </div>

                <div class="content">
                    <div class="sidebar" id="sidebar">
                        <div class="sidebar-title">On this page</div>
                        {sidebar_nav}
                    </div>

                    <div class="main-content" id="mainContent">
                        <form method="POST" id="reflectionForm">
                            <div class="tab-content active" id="report">
                                <div class="report-content">{html_content}</div>
                            </div>

                            <div class="tab-content" id="reflections" style="max-width: 700px;">
                                {reflection_form}
                            </div>

                            <div class="footer">
                                <div>
                                    <button type="submit" name="action" value="save" class="btn btn-primary">Save Reflections &amp; Close</button>
                                    <button type="submit" name="action" value="skip" class="btn btn-secondary">Skip</button>
                                </div>
                                <button type="submit" name="action" value="disable" class="btn btn-danger">Disable Scheduling</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>

            <script>
                function toggleTheme() {{
                    const html = document.documentElement;
                    const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
                    html.setAttribute('data-theme', next);
                    document.getElementById('themeIcon').innerHTML = next === 'dark' ? '&#9789;' : '&#9788;';
                    document.getElementById('themeLabel').textContent = next === 'dark' ? 'LIGHT' : 'DARK';
                }}

                function showTab(tabName, btn) {{
                    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    document.getElementById(tabName).classList.add('active');
                    if (btn) btn.classList.add('active');
                    document.getElementById('sidebar').style.display = tabName === 'report' ? '' : 'none';
                }}

                // Smooth scroll sidebar links
                document.querySelectorAll('.sidebar-link').forEach(link => {{
                    link.addEventListener('click', function(e) {{
                        e.preventDefault();
                        const target = document.getElementById(this.getAttribute('href').substring(1));
                        if (target) target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                    }});
                }});

                // Form submission confirmation for disable
                document.getElementById('reflectionForm').addEventListener('submit', function(e) {{
                    if (e.submitter.value === 'disable') {{
                        if (!confirm('Are you sure you want to disable all scheduled reports?')) {{
                            e.preventDefault();
                        }}
                    }}
                }});

                // Activate first sidebar link
                const firstLink = document.querySelector('.sidebar-link');
                if (firstLink) firstLink.classList.add('active');
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
                answer = answers.get(question.lower().replace(' ', '_').replace('?', ''), '').strip()
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