"""
GUI popup interface for report display and reflection input
"""

import os
import platform
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

# GUI availability check
def gui_available(skip_test=False) -> bool:
    """Check if GUI can be displayed"""
    # If caller wants to skip the test (e.g., when they know they want terminal), return False
    if skip_test:
        return False

    # If caller wants to skip the test (e.g., when they know they want terminal), return False
    if skip_test:
        return False

    # Quick environment checks first (no imports needed)

    # Check for SSH session
    if 'SSH_CLIENT' in os.environ or 'SSH_TTY' in os.environ:
        return False

    # Check platform-specific requirements
    if platform.system() == 'Linux':
        # Check for DISPLAY environment variable
        if not os.environ.get('DISPLAY'):
            return False
    elif platform.system() == 'Darwin':  # macOS
        # On macOS, GUI should generally be available unless in specific cases
        if os.environ.get('TERM') and 'screen' in os.environ.get('TERM', ''):
            # Screen/tmux sessions might not support GUI
            return False
    elif platform.system() == 'Windows':
        # Windows should generally support GUI
        pass
    else:
        # Unknown platform, assume no GUI
        return False

    # Try tkinter with minimal testing
    try:
        import tkinter as tk
        # Simple test - just try to import and check if we can create a Tk instance
        # Don't actually create the window to avoid the compatibility error
        try:
            # Test if tkinter can be initialized
            test_root = tk.Tk()
            test_root.withdraw()  # Hide immediately
            test_root.quit()
            test_root.destroy()
            return True
        except Exception as e:
            # If we get the specific macOS version error, that's actually about ttkbootstrap
            # Basic tkinter might still work
            error_msg = str(e).lower()
            if 'macos' in error_msg and 'required' in error_msg:
                # This is likely the ttkbootstrap version error, try basic tkinter
                return True
            return False
    except ImportError:
        return False
    except Exception:
        return False


class ReportPopup:
    """GUI popup for displaying reports and collecting reflections"""

    def __init__(self, report_content: str, report_path: str):
        self.report_content = report_content
        self.report_path = Path(report_path)
        self.reflection_answers = {}
        self.result = None
        self.root = None

        # Reflection questions (imported from cli.py pattern)
        self.reflection_questions = [
            ("What could I have done better?", "### What could I have done better?"),
            ("What is important that I am missing?", "### What is important that I am missing?"),
            ("Am I doing work that is aligned with my goals?", "### Am I doing work that is aligned with my goals?"),
            ("How do I feel?", "### How do I feel?"),
        ]

    def show(self) -> Optional[str]:
        """Display popup and wait for user interaction"""
        try:
            import tkinter as tk
            from tkinter import ttk, scrolledtext, messagebox
        except ImportError:
            console.print("❌ GUI libraries not available. Falling back to terminal.", style="yellow")
            return self._show_terminal_fallback()

        try:
            # Create main window with modern styling
            self.root = tk.Tk()

            # Modern color scheme
            bg_color = '#f8f9fa'
            accent_color = '#007bff'
            text_color = '#212529'

            self.root.configure(bg=bg_color)

            self.root.title("📊 Report & Reflection")
            self.root.geometry("1000x800")

            # Make the window appear on top and focused
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.after_idle(lambda: self.root.attributes('-topmost', False))

            self._setup_gui()

            # Center the window
            self._center_window()

            # Start the GUI event loop
            self.root.mainloop()

            return self.result

        except Exception as e:
            console.print(f"❌ GUI error: {e}. Falling back to terminal.", style="yellow")
            return self._show_terminal_fallback()

    def _setup_gui(self):
        """Create the main GUI layout"""
        import tkinter as tk
        from tkinter import ttk, scrolledtext

        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')  # More modern than default

        # Main container with modern styling
        main_frame = tk.Frame(self.root, bg=bg_color, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title with modern typography
        title_label = tk.Label(
            main_frame,
            text="📊 Generated Report & Reflection Time",
            font=('SF Pro Display', 18, 'bold') if platform.system() == 'Darwin' else ('Segoe UI', 16, 'bold'),
            bg=bg_color,
            fg=text_color
        )
        title_label.pack(pady=(0, 15))

        # Create notebook for tabs with styling
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Report tab
        self._create_report_tab(notebook)

        # Reflection tab
        self._create_reflection_tab(notebook)

        # Buttons frame with modern styling
        buttons_frame = tk.Frame(main_frame, bg=bg_color)
        buttons_frame.pack(fill=tk.X, pady=(15, 0))

        # Modern button styling
        button_font = ('SF Pro Display', 12) if platform.system() == 'Darwin' else ('Segoe UI', 11)

        # Primary save button
        save_btn = tk.Button(
            buttons_frame,
            text="💾 Save Reflections & Close",
            command=self._save_and_close,
            bg=accent_color,
            fg='white',
            font=button_font,
            relief='flat',
            padx=15,
            pady=8,
            cursor='hand2'
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Secondary skip button
        skip_btn = tk.Button(
            buttons_frame,
            text="⏭️ Skip Reflections",
            command=self._skip_reflections,
            bg='#6c757d',
            fg='white',
            font=button_font,
            relief='flat',
            padx=15,
            pady=8,
            cursor='hand2'
        )
        skip_btn.pack(side=tk.LEFT, padx=5)

        # Warning disable button
        disable_btn = tk.Button(
            buttons_frame,
            text="🚫 Disable Scheduling",
            command=self._disable_scheduling,
            bg='#dc3545',
            fg='white',
            font=button_font,
            relief='flat',
            padx=15,
            pady=8,
            cursor='hand2'
        )
        disable_btn.pack(side=tk.RIGHT)

        # Focus on the first reflection field
        notebook.select(1)  # Select reflection tab

    def _create_report_tab(self, parent):
        """Create the report display tab"""
        import tkinter as tk
        from tkinter import scrolledtext

        report_frame = ttk.Frame(parent)
        parent.add(report_frame, text="📄 Report")

        # Report content area
        report_text = scrolledtext.ScrolledText(
            report_frame,
            wrap=tk.WORD,
            font=('Monaco', 11) if platform.system() == 'Darwin' else ('Consolas', 10),
            height=25
        )
        report_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Insert the report content
        report_text.insert('1.0', self.report_content)
        report_text.config(state=tk.DISABLED)  # Make read-only

    def _create_reflection_tab(self, parent):
        """Create the reflection input tab"""
        import tkinter as tk
        from tkinter import scrolledtext

        reflection_frame = ttk.Frame(parent)
        parent.add(reflection_frame, text="🤔 Reflections")

        # Create scrollable frame for reflections
        canvas = tk.Canvas(reflection_frame)
        scrollbar = ttk.Scrollbar(reflection_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Add reflection questions
        self.reflection_widgets = {}

        for i, (question, _) in enumerate(self.reflection_questions):
            question_frame = ttk.LabelFrame(scrollable_frame, text=question, padding="10")
            question_frame.pack(fill=tk.X, padx=10, pady=5)

            text_widget = scrolledtext.ScrolledText(
                question_frame,
                height=4,
                wrap=tk.WORD,
                font=('TkDefaultFont', 10)
            )
            text_widget.pack(fill=tk.X)

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

    def _center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

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
            import tkinter.messagebox as messagebox
            messagebox.showerror("Error", f"Failed to save reflections: {e}")
            return

        self.root.destroy()

    def _skip_reflections(self):
        """Skip reflections and close"""
        self.result = "skipped"
        self.root.destroy()

    def _disable_scheduling(self):
        """Disable scheduling and close"""
        import tkinter.messagebox as messagebox

        if messagebox.askyesno(
            "Disable Scheduling",
            "Are you sure you want to disable automated report scheduling?\n\n"
            "You can re-enable it later using: receipts schedule daily/weekly"
        ):
            self.result = "disable"
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
                reflection_section += f"{header}\n\n{answer}\n\n"
            else:
                reflection_section += f"{header}\n\n*[Add your thoughts]*\n\n"

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

    def _show_terminal_fallback(self) -> Optional[str]:
        """Fallback to terminal interface when GUI is not available"""
        terminal_display = TerminalReportDisplay()
        return terminal_display.show_report_with_reflections(self.report_content, str(self.report_path))


class TerminalReportDisplay:
    """Terminal fallback for report display and reflection input"""

    def __init__(self):
        self.reflection_questions = [
            ("What could I have done better?", "### What could I have done better?"),
            ("What is important that I am missing?", "### What is important that I am missing?"),
            ("Am I doing work that is aligned with my goals?", "### Am I doing work that is aligned with my goals?"),
            ("How do I feel?", "### How do I feel?"),
        ]

    def show_report_with_reflections(self, report_content: str, report_path: str) -> Optional[str]:
        """Show report and collect reflections in terminal"""

        # Display banner
        console.print("\n" + "="*80)
        console.print("📊 [bold]Generated Report & Reflection Time[/bold]", style="cyan", justify="center")
        console.print("="*80)

        # Show report content
        console.print("\n📄 [bold]Report Content:[/bold]\n")
        report_panel = Panel(
            Markdown(report_content),
            title="📊 Report",
            border_style="blue"
        )
        console.print(report_panel)

        # Ask user what they want to do
        console.print("\n🤔 [bold]What would you like to do?[/bold]")
        choice = Prompt.ask(
            "Choose an option",
            choices=["reflect", "skip", "disable"],
            default="reflect",
            show_choices=True
        )

        if choice == "reflect":
            return self._collect_reflections(report_path)
        elif choice == "skip":
            console.print("⏭️ Skipping reflections", style="yellow")
            return "skipped"
        elif choice == "disable":
            if click.confirm("Are you sure you want to disable automated report scheduling?"):
                return "disable"
            else:
                return self._collect_reflections(report_path)

    def _collect_reflections(self, report_path: str) -> str:
        """Collect reflection responses via terminal prompts"""
        console.print("\n🤔 [bold]Reflection Time[/bold]")
        console.print("Please answer the following questions (press Enter twice to finish each answer):\n")

        reflection_answers = {}

        for question, header in self.reflection_questions:
            console.print(f"[bold cyan]{question}[/bold cyan]")

            lines = []
            console.print("(Type your answer, then press Enter twice when done)")

            while True:
                try:
                    line = input()
                    if line == "" and lines:
                        break
                    lines.append(line)
                except KeyboardInterrupt:
                    console.print("\n⚠️ Reflection cancelled", style="yellow")
                    return "skipped"

            answer = "\n".join(lines).strip()
            reflection_answers[question] = answer

        # Update the report file
        try:
            self._update_report_with_reflections(report_path, reflection_answers)
            console.print("✅ Reflections saved successfully!", style="green")
            return "saved"
        except Exception as e:
            console.print(f"❌ Failed to save reflections: {e}", style="red")
            return "error"

    def _update_report_with_reflections(self, report_path: str, reflection_answers: Dict[str, str]):
        """Update the markdown file with reflection responses"""
        path = Path(report_path)
        if not path.exists():
            raise FileNotFoundError(f"Report file not found: {path}")

        # Read current content
        content = path.read_text()

        # Build reflection section
        reflection_section = "\n\n## 🤔 Reflections\n\n"

        for question, header in self.reflection_questions:
            answer = reflection_answers.get(question, "").strip()
            if answer:
                reflection_section += f"{header}\n\n{answer}\n\n"
            else:
                reflection_section += f"{header}\n\n*[Add your thoughts]*\n\n"

        # Check if reflections already exist
        if "## 🤔 Reflections" in content:
            # Replace existing reflections
            parts = content.split("## 🤔 Reflections")
            before_reflections = parts[0]

            # Find the end of reflections section
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
        path.write_text(new_content)