"""
AppleScript-based native popup for macOS - most reliable option
"""

import subprocess
import platform
import tempfile
import os
import time
from pathlib import Path
from typing import Optional, Dict
import json

from rich.console import Console

console = Console()


class AppleScriptPopup:
    """Native macOS popup using AppleScript"""

    def __init__(self, report_content: str, report_path: str):
        self.report_content = report_content
        self.report_path = Path(report_path)
        self.reflection_questions = [
            ("What could I have done better?", "What could I have done better?"),
            ("What is important that I am missing?", "What is important that I am missing?"),
            ("Am I doing work that is aligned with my goals?", "Am I doing work that is aligned with my goals?"),
            ("How do I feel?", "How do I feel?"),
        ]

    def show(self) -> Optional[str]:
        """Display native popup and wait for user interaction"""
        if platform.system() != 'Darwin':
            return None

        try:
            # Extract a summary from the report for the dialog
            report_summary = self._extract_summary()

            # First, show the full report content in a scrollable dialog
            console.print("🖥️ Opening native macOS report viewer...")

            # Create a more comprehensive report view
            full_report_lines = self.report_content.split('\n')

            # Show key sections of the report
            preview_lines = []
            lines_added = 0
            max_lines = 40

            for line in full_report_lines:
                if lines_added >= max_lines:
                    break

                # Include headers and important content
                if (line.startswith('#') or
                    'GitHub Activity' in line or
                    'Key Achievements' in line or
                    'Pull Requests Created' in line or
                    'contributions' in line or
                    'meetings' in line or
                    line.startswith('  •') or
                    line.strip().startswith('•')):
                    preview_lines.append(line)
                    lines_added += 1

            report_preview = "\\n".join(preview_lines)

            if len(full_report_lines) > max_lines:
                report_preview += "\\n\\n... (complete report available - click 'View Complete Report')"

            # Escape for AppleScript and limit length
            report_preview = report_preview.replace('"', '\\"')
            if len(report_preview) > 2000:
                report_preview = report_preview[:1900] + "...\\n\\n(truncated - click 'View Complete Report' for full version)"

            report_script = f'''
            display dialog "{report_preview}\\n\\n(Auto-closes in 3 minutes)" ¬
                buttons {{"View Complete Report", "Continue to Reflections"}} ¬
                default button "Continue to Reflections" ¬
                with title "📊 Your Productivity Report" ¬
                with icon 1 ¬
                giving up after 180

            set buttonPressed to button returned of result

            if buttonPressed is "View Complete Report" then
                return "view_full"
            else
                return "continue"
            end if
            '''

            try:
                result = subprocess.run(['osascript', '-e', report_script],
                                      capture_output=True, text=True, check=True)
                choice = result.stdout.strip()
            except subprocess.CalledProcessError:
                choice = "continue"

            # If user wants to see complete report, open it in default app
            if choice == "view_full":
                # Create temporary file and open with default app
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, prefix='receipts_report_') as f:
                    f.write(self.report_content)
                    temp_report_path = f.name

                subprocess.run(['open', temp_report_path])
                console.print("📖 Complete report opened in default app")

                # Give user time to read
                time.sleep(3)
            else:
                temp_report_path = None

            # Show reflection dialog
            console.print("🤔 Opening reflection dialog...")

            choice = self._show_choice_dialog()

            if choice == "reflect":
                # Collect reflections
                reflections = self._collect_reflections()
                if reflections:
                    self._save_reflections(reflections)
                    return "saved"
                else:
                    return "cancelled"
            elif choice == "skip":
                return "skipped"
            elif choice == "disable":
                return "disable"
            else:
                return "cancelled"

        except Exception as e:
            console.print(f"❌ AppleScript popup failed: {e}", style="red")
            return None
        finally:
            # Clean up temp file
            if 'temp_report_path' in locals() and temp_report_path:
                try:
                    os.unlink(temp_report_path)
                except:
                    pass

    def _extract_summary(self) -> str:
        """Extract a brief summary from the report for the dialog"""
        lines = self.report_content.split('\n')

        # Look for key metrics
        summary_parts = []

        for line in lines:
            line = line.strip()
            if ('GitHub contributions' in line and 'total' in line) or \
               ('Pull Requests Created' in line and ':' in line) or \
               ('code reviews completed' in line) or \
               ('meetings attended' in line) or \
               ('hours in meetings' in line):
                # Clean up the line and add it
                clean_line = line.replace('•', '').strip()
                if clean_line and len(clean_line) < 80:  # Keep it reasonable
                    summary_parts.append(clean_line)

        if summary_parts:
            summary = "📊 Today's Highlights:\\n\\n" + "\\n".join(summary_parts[:5])  # Top 5 items
        else:
            # Fallback - just show it's a report
            summary = "📊 Your productivity report is ready!\\n\\nWould you like to add reflections?"

        # Limit length for dialog
        if len(summary) > 400:
            summary = summary[:400] + "..."

        return summary

    def _show_choice_dialog(self) -> str:
        """Show the main choice dialog"""
        script = '''
        display dialog "What would you like to do with this report?\\n\\n📝 Add personal reflections to help you grow\\n⏭️ Skip reflections for now\\n🚫 Disable automated reports\\n\\n(Auto-closes in 3 minutes)" ¬
            buttons {"Skip Reflections", "Add Reflections", "Disable Scheduling"} ¬
            default button "Add Reflections" ¬
            with title "🤔 Reflection Time" ¬
            with icon 1 ¬
            giving up after 180

        set buttonPressed to button returned of result

        if buttonPressed is "Add Reflections" then
            return "reflect"
        else if buttonPressed is "Skip Reflections" then
            return "skip"
        else if buttonPressed is "Disable Scheduling" then
            return "disable"
        else
            return "skip"
        end if
        '''

        try:
            result = subprocess.run(['osascript', '-e', script],
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "cancelled"

    def _collect_reflections(self) -> Dict[str, str]:
        """Collect reflection answers using AppleScript dialogs"""
        reflections = {}

        for i, (question, _) in enumerate(self.reflection_questions):
            # Create AppleScript dialog for each question
            progress_text = f"Question {i+1} of {len(self.reflection_questions)}"

            script = f'''
            display dialog "{question}\\n\\n💭 Take your time to reflect...\\n\\n({progress_text} • Auto-closes in 5 minutes)" ¬
                default answer "" ¬
                buttons {{"Skip This", "Save & Next"}} ¬
                default button "Save & Next" ¬
                with title "🤔 Reflection Time" ¬
                with icon 1 ¬
                giving up after 300

            set buttonPressed to button returned of result
            set textReturned to text returned of result

            if buttonPressed is "Save & Next" then
                return textReturned
            else
                return ""
            end if
            '''

            try:
                result = subprocess.run(['osascript', '-e', script],
                                      capture_output=True, text=True, check=True)
                answer = result.stdout.strip()
                reflections[question] = answer

                # Show progress
                console.print(f"✅ Reflection {i+1}/{len(self.reflection_questions)} {'saved' if answer else 'skipped'}")

            except subprocess.CalledProcessError:
                # User cancelled, stop collecting
                console.print(f"⏭️ Remaining reflections cancelled")
                break

        return reflections

    def _save_reflections(self, reflections: Dict[str, str]):
        """Save reflections to the markdown file"""
        try:
            content = self.report_path.read_text()

            # Build reflection section
            reflection_section = "\n\n## 🤔 Reflections\n\n"

            for question, header in self.reflection_questions:
                answer = reflections.get(question, "").strip()
                if answer:
                    reflection_section += f"### {header}\n\n{answer}\n\n"
                else:
                    reflection_section += f"### {header}\n\n*[Add your thoughts]*\n\n"

            # Update the file
            if "## 🤔 Reflections" in content:
                # Replace existing reflections
                parts = content.split("## 🤔 Reflections")
                before_reflections = parts[0]
                new_content = before_reflections + reflection_section.rstrip()
            else:
                # Append reflections
                new_content = content + reflection_section

            self.report_path.write_text(new_content)

        except Exception as e:
            console.print(f"❌ Failed to save reflections: {e}", style="red")
            raise


def applescript_available() -> bool:
    """Check if AppleScript popup is available (macOS only)"""
    if platform.system() != 'Darwin':
        return False

    try:
        # Test if osascript is available
        subprocess.run(['osascript', '-e', 'return "test"'],
                      capture_output=True, check=True)
        return True
    except:
        return False