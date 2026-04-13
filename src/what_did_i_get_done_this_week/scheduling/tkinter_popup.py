"""
Modern tkinter-based popup interface - more reliable than webview
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import platform
from pathlib import Path
from typing import Optional, Dict
import html
import re

from rich.console import Console

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

console = Console()

try:
    import tkinter as tk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False


class ModernTkinterPopup:
    """Modern tkinter popup for displaying reports and collecting reflections"""

    def __init__(self, report_content: str, report_path: str):
        self.full_content = report_content
        self.report_path = Path(report_path)

        # Separate report content from any existing reflections
        self.report_content = self._extract_report_content(report_content)

        self.reflection_questions = [
            ("What could I have done better?", "What could I have done better?"),
            ("What is important that I am missing?", "What is important that I am missing?"),
            ("Am I doing work that is aligned with my goals?", "Am I doing work that is aligned with my goals?"),
            ("How do I feel?", "How do I feel?"),
        ]
        self.result = None
        self.reflection_answers = {}
        self.root = None

    def show(self) -> Optional[str]:
        """Display popup and wait for user interaction"""
        if not TKINTER_AVAILABLE:
            console.print("❌ tkinter not available", style="yellow")
            return None

        try:
            # Create the main window
            self.root = tk.Tk()
            self._setup_window()
            self._create_interface()

            # Start the GUI event loop
            self.root.mainloop()

            return self.result

        except Exception as e:
            console.print(f"❌ Tkinter popup failed: {e}", style="red")
            return None

    def _setup_window(self):
        """Configure the main window"""
        self.root.title("📊 Reflection Time - What Did I Get Done?")
        self.root.geometry("1200x800")

        # Clean, simple color scheme
        bg_color = '#ffffff'
        self.root.configure(bg=bg_color)

        # Center the window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

        # Make it appear on top
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(lambda: self.root.attributes('-topmost', False))

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_interface(self):
        """Create the main interface"""
        # Main container
        main_frame = tk.Frame(self.root, bg='#ffffff')
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = tk.Frame(main_frame, bg='#2c3e50', height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        title_label = tk.Label(
            header_frame,
            text="📊 Generated Report & Reflection Time",
            font=('System', 14, 'bold'),
            bg='#2c3e50',
            fg='white'
        )
        title_label.pack(expand=True)

        # Content area with notebook
        content_frame = tk.Frame(main_frame, bg='#ffffff')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Create notebook for tabs
        style = ttk.Style()
        style.theme_use('clam')

        notebook = ttk.Notebook(content_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Report tab
        report_frame = tk.Frame(notebook, bg='white')
        notebook.add(report_frame, text='📄 Report')

        report_text = scrolledtext.ScrolledText(
            report_frame,
            wrap=tk.WORD,
            font=('Monaco', 11) if platform.system() == 'Darwin' else ('Consolas', 10),
            bg='#ffffff',
            fg='#333333',
            relief='flat',
            borderwidth=1,
            padx=15,
            pady=15
        )
        report_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Just insert the raw content - no complex parsing needed
        report_text.insert('1.0', self.report_content)
        report_text.config(state=tk.DISABLED)

        # Reflection tab
        reflection_frame = tk.Frame(notebook, bg='white')
        notebook.add(reflection_frame, text='🤔 Reflections')

        # Make sure Report tab is selected by default
        notebook.select(0)

        # Scrollable frame for reflections
        canvas = tk.Canvas(reflection_frame, bg='white')
        scrollbar = ttk.Scrollbar(reflection_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Add reflection questions
        self.reflection_widgets = {}

        for i, (question, _) in enumerate(self.reflection_questions):
            question_frame = tk.LabelFrame(
                scrollable_frame,
                text=question,
                font=('SF Pro Display', 12, 'bold') if platform.system() == 'Darwin' else ('Segoe UI', 11, 'bold'),
                bg='white',
                fg='#495057',
                padx=15,
                pady=10
            )
            question_frame.pack(fill=tk.X, padx=20, pady=10)

            text_widget = scrolledtext.ScrolledText(
                question_frame,
                height=4,
                wrap=tk.WORD,
                font=('System', 11),
                relief='solid',
                borderwidth=1,
                bg='#ffffff',
                fg='#333333',
                padx=10,
                pady=8
            )
            text_widget.pack(fill=tk.X, pady=5)

            self.reflection_widgets[question] = text_widget

            # Auto-focus first field
            if i == 0:
                text_widget.focus_set()

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Prevent Enter key from triggering default button behavior in text areas
        def _on_text_enter(event):
            # Allow normal text insertion instead of triggering button
            return "break"

        for widget in self.reflection_widgets.values():
            widget.bind("<Return>", _on_text_enter)
            # Allow Ctrl+Enter to create new lines
            widget.bind("<Control-Return>", lambda e: e.widget.insert(tk.INSERT, '\n'))

        # Footer with buttons
        footer_frame = tk.Frame(main_frame, bg='#f8f9fa', height=70)
        footer_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        footer_frame.pack_propagate(False)

        button_frame = tk.Frame(footer_frame, bg='#f8f9fa')
        button_frame.pack(expand=True)

        # Simple button styling with good contrast
        button_font = ('System', 11, 'normal')

        # Primary save button
        save_btn = tk.Button(
            button_frame,
            text="Save Reflections & Close",
            command=self._save_and_close,
            bg='#27ae60',
            fg='white',
            font=button_font,
            relief='raised',
            bd=2,
            padx=20,
            pady=8,
            cursor='hand2',
            activebackground='#229954',
            activeforeground='white'
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Secondary skip button
        skip_btn = tk.Button(
            button_frame,
            text="Skip Reflections",
            command=self._skip_reflections,
            bg='#95a5a6',
            fg='white',
            font=button_font,
            relief='raised',
            bd=2,
            padx=20,
            pady=8,
            cursor='hand2',
            activebackground='#7f8c8d',
            activeforeground='white'
        )
        skip_btn.pack(side=tk.LEFT, padx=5)

        # Warning disable button
        disable_btn = tk.Button(
            button_frame,
            text="Disable Scheduling",
            command=self._disable_scheduling,
            bg='#e74c3c',
            fg='white',
            font=button_font,
            relief='raised',
            bd=2,
            padx=20,
            pady=8,
            cursor='hand2',
            activebackground='#c0392b',
            activeforeground='white'
        )
        disable_btn.pack(side=tk.RIGHT)

    def _save_and_close(self):
        """Save reflections and close popup"""
        # Collect reflection answers
        for question, widget in self.reflection_widgets.items():
            answer = widget.get('1.0', 'end-1c').strip()
            self.reflection_answers[question] = answer

        # Save to file
        try:
            self._update_report_with_reflections()
            self.result = "saved"
            console.print("✅ Reflections saved successfully!", style="green")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save reflections: {e}")
            return

        self.root.destroy()

    def _skip_reflections(self):
        """Skip reflections and close"""
        self.result = "skipped"
        self.root.destroy()

    def _disable_scheduling(self):
        """Disable scheduling and close"""
        if messagebox.askyesno(
            "Disable Scheduling",
            "Are you sure you want to disable automated report scheduling?\n\n"
            "You can re-enable it later using: receipts schedule daily/weekly"
        ):
            self.result = "disable"
            self.root.destroy()

    def _on_closing(self):
        """Handle window close event"""
        if not self.result:
            self.result = "cancelled"
        self.root.destroy()

    def _update_report_with_reflections(self):
        """Update the markdown file with reflection responses"""
        if not self.report_path.exists():
            raise FileNotFoundError(f"Report file not found: {self.report_path}")

        # Read current content
        content = self.report_path.read_text()

        # Find or create reflection section
        reflection_section = "\n\n## 🤔 Reflections\n\n"

        for question, header in self.reflection_questions:
            answer = self.reflection_answers.get(question, "").strip()
            if answer:
                reflection_section += f"### {header}\n\n{answer}\n\n"
            else:
                reflection_section += f"### {header}\n\n*[Add your thoughts]*\n\n"

        # Check if reflections already exist
        if "## 🤔 Reflections" in content:
            # Replace existing reflections
            parts = content.split("## 🤔 Reflections")
            before_reflections = parts[0]

            # Find the end of reflections section (next ## header or end of file)
            if len(parts) > 1:
                remaining = parts[1]
                next_section_match = None
                for line in remaining.split('\n'):
                    if line.strip().startswith('## ') and '🤔 Reflections' not in line:
                        next_section_match = line
                        break

                if next_section_match:
                    after_reflections = '\n' + remaining[remaining.find(next_section_match):]
                else:
                    after_reflections = ""
            else:
                after_reflections = ""

            new_content = before_reflections + reflection_section.rstrip() + after_reflections
        else:
            # Append reflections
            new_content = content + reflection_section

        # Write back to file
        self.report_path.write_text(new_content)

    def _extract_report_content(self, full_content: str) -> str:
        """Extract only the report content, excluding any existing reflections"""
        if "## 🤔 Reflections" in full_content:
            # Split on the reflections header and take only the part before it
            parts = full_content.split("## 🤔 Reflections")
            return parts[0].rstrip()
        return full_content


def modern_tkinter_available() -> bool:
    """Check if modern tkinter popup is available"""
    if not TKINTER_AVAILABLE:
        return False

    try:
        # Quick test to see if we can create a Tk instance
        test_root = tk.Tk()
        test_root.withdraw()
        test_root.destroy()
        return True
    except Exception:
        return False