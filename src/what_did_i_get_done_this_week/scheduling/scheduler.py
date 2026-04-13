"""
Cross-platform scheduling management for automated report generation
"""

import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from rich.console import Console
from rich.table import Table

console = Console()


class ScheduleManager:
    """Manages scheduled jobs across different platforms"""

    def __init__(self):
        self.platform = platform.system().lower()
        self.python_executable = sys.executable

    def setup_daily_schedule(self, time_str: str, popup: bool = True) -> bool:
        """Install daily cron job for yesterday's report"""
        try:
            hour, minute = time_str.split(':')
            cron_time = f"{minute} {hour} * * *"

            command = self._build_scheduled_command('daily', popup)
            comment = "receipts-daily-report"

            return self._install_schedule(cron_time, command, comment)
        except Exception as e:
            console.print(f"❌ Failed to setup daily schedule: {e}", style="red")
            return False

    def setup_weekly_schedule(self, time_str: str, day: str, popup: bool = True) -> bool:
        """Install weekly cron job for last week's report"""
        try:
            hour, minute = time_str.split(':')
            day_num = self._day_to_number(day)
            cron_time = f"{minute} {hour} * * {day_num}"

            command = self._build_scheduled_command('weekly', popup)
            comment = "receipts-weekly-report"

            return self._install_schedule(cron_time, command, comment)
        except Exception as e:
            console.print(f"❌ Failed to setup weekly schedule: {e}", style="red")
            return False

    def remove_all_schedules(self) -> bool:
        """Remove all scheduled jobs"""
        try:
            if self.platform in ['linux', 'darwin']:  # Linux/macOS
                return self._remove_cron_schedules()
            elif self.platform == 'windows':
                return self._remove_windows_schedules()
            else:
                console.print(f"❌ Unsupported platform: {self.platform}", style="red")
                return False
        except Exception as e:
            console.print(f"❌ Failed to remove schedules: {e}", style="red")
            return False

    def get_schedule_status(self) -> Dict[str, Dict]:
        """Return current schedule status"""
        try:
            if self.platform in ['linux', 'darwin']:
                return self._get_cron_status()
            elif self.platform == 'windows':
                return self._get_windows_status()
            else:
                return {"error": f"Unsupported platform: {self.platform}"}
        except Exception as e:
            return {"error": str(e)}

    def _build_scheduled_command(self, report_type: str, popup: bool) -> str:
        """Build the command to run for scheduled reports"""
        popup_flag = "" if popup else " --no-popup"
        return f'"{self.python_executable}" -m what_did_i_get_done_this_week.scheduled_run {report_type}{popup_flag}'

    def _day_to_number(self, day: str) -> str:
        """Convert day name to cron day number (0=Sunday, 1=Monday, etc.)"""
        days = {
            'sunday': '0',
            'monday': '1',
            'tuesday': '2',
            'wednesday': '3',
            'thursday': '4',
            'friday': '5',
            'saturday': '6'
        }
        return days.get(day.lower(), '1')  # Default to Monday

    def _install_schedule(self, cron_time: str, command: str, comment: str) -> bool:
        """Install schedule based on platform"""
        if self.platform in ['linux', 'darwin']:
            return self._install_cron_job(cron_time, command, comment)
        elif self.platform == 'windows':
            return self._install_windows_task(cron_time, command, comment)
        return False

    def _install_cron_job(self, cron_time: str, command: str, comment: str) -> bool:
        """Install cron job on Linux/macOS"""
        try:
            from crontab import CronTab

            # Get user's crontab
            cron = CronTab(user=True)

            # Remove existing job with same comment
            cron.remove_all(comment=comment)

            # Create new job
            job = cron.new(command=command, comment=comment)
            job.setall(cron_time)

            # Write crontab
            cron.write()

            console.print(f"✅ Installed cron job: {cron_time} {command}", style="green")
            return True

        except ImportError:
            # Fallback to crontab command
            return self._install_cron_fallback(cron_time, command, comment)
        except Exception as e:
            console.print(f"❌ Failed to install cron job: {e}", style="red")
            return False

    def _install_cron_fallback(self, cron_time: str, command: str, comment: str) -> bool:
        """Fallback cron installation using crontab command"""
        try:
            # Get current crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            existing_crontab = result.stdout if result.returncode == 0 else ""

            # Remove existing entries with same comment
            lines = []
            for line in existing_crontab.split('\n'):
                if line.strip() and not line.strip().endswith(f"# {comment}"):
                    lines.append(line)

            # Add new entry
            new_entry = f"{cron_time} {command} # {comment}"
            lines.append(new_entry)

            # Write new crontab
            new_crontab = '\n'.join(lines) + '\n'
            proc = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
            proc.communicate(input=new_crontab)

            if proc.returncode == 0:
                console.print(f"✅ Installed cron job: {new_entry}", style="green")
                return True
            else:
                console.print("❌ Failed to install cron job", style="red")
                return False

        except Exception as e:
            console.print(f"❌ Failed to install cron job: {e}", style="red")
            return False

    def _install_windows_task(self, cron_time: str, command: str, comment: str) -> bool:
        """Install Windows Task Scheduler task"""
        try:
            # Convert cron time to Windows Task Scheduler format
            parts = cron_time.split()
            minute, hour = parts[0], parts[1]

            if parts[4] != '*':  # Weekly task
                day = parts[4]
                days_map = {'0': 'SUN', '1': 'MON', '2': 'TUE', '3': 'WED',
                           '4': 'THU', '5': 'FRI', '6': 'SAT'}
                schedule_type = "WEEKLY"
                day_arg = f"/d {days_map.get(day, 'MON')}"
            else:  # Daily task
                schedule_type = "DAILY"
                day_arg = ""

            task_name = f"receipts-{comment.split('-')[1]}-report"

            # Create the scheduled task
            cmd = [
                'schtasks', '/create', '/f',
                '/tn', task_name,
                '/tr', command,
                '/sc', schedule_type,
                '/st', f"{hour}:{minute}",
                day_arg
            ]

            # Remove empty arguments
            cmd = [arg for arg in cmd if arg]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                console.print(f"✅ Created Windows task: {task_name}", style="green")
                return True
            else:
                console.print(f"❌ Failed to create Windows task: {result.stderr}", style="red")
                return False

        except Exception as e:
            console.print(f"❌ Failed to create Windows task: {e}", style="red")
            return False

    def _remove_cron_schedules(self) -> bool:
        """Remove cron schedules on Linux/macOS"""
        try:
            from crontab import CronTab

            cron = CronTab(user=True)
            removed_count = 0

            # Remove jobs with our comments
            for comment in ['receipts-daily-report', 'receipts-weekly-report']:
                removed = cron.remove_all(comment=comment)
                removed_count += removed

            cron.write()

            if removed_count > 0:
                console.print(f"✅ Removed {removed_count} scheduled job(s)", style="green")
            else:
                console.print("ℹ️  No scheduled jobs found to remove", style="yellow")

            return True

        except ImportError:
            return self._remove_cron_fallback()
        except Exception as e:
            console.print(f"❌ Failed to remove cron schedules: {e}", style="red")
            return False

    def _remove_cron_fallback(self) -> bool:
        """Fallback cron removal using crontab command"""
        try:
            # Get current crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode != 0:
                console.print("ℹ️  No crontab found", style="yellow")
                return True

            existing_crontab = result.stdout
            lines = []
            removed_count = 0

            # Filter out our entries
            for line in existing_crontab.split('\n'):
                if line.strip() and not any(comment in line for comment in
                                          ['receipts-daily-report', 'receipts-weekly-report']):
                    lines.append(line)
                elif line.strip():
                    removed_count += 1

            # Write new crontab
            new_crontab = '\n'.join(lines) + '\n' if lines else ''
            if new_crontab.strip():
                proc = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
                proc.communicate(input=new_crontab)
            else:
                # Remove entire crontab if empty
                subprocess.run(['crontab', '-r'], capture_output=True)

            if removed_count > 0:
                console.print(f"✅ Removed {removed_count} scheduled job(s)", style="green")
            else:
                console.print("ℹ️  No scheduled jobs found to remove", style="yellow")

            return True

        except Exception as e:
            console.print(f"❌ Failed to remove cron schedules: {e}", style="red")
            return False

    def _remove_windows_schedules(self) -> bool:
        """Remove Windows Task Scheduler tasks"""
        try:
            task_names = ['receipts-daily-report', 'receipts-weekly-report']
            removed_count = 0

            for task_name in task_names:
                result = subprocess.run(
                    ['schtasks', '/delete', '/tn', task_name, '/f'],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    removed_count += 1

            if removed_count > 0:
                console.print(f"✅ Removed {removed_count} scheduled task(s)", style="green")
            else:
                console.print("ℹ️  No scheduled tasks found to remove", style="yellow")

            return True

        except Exception as e:
            console.print(f"❌ Failed to remove Windows schedules: {e}", style="red")
            return False

    def _get_cron_status(self) -> Dict[str, Dict]:
        """Get cron schedule status on Linux/macOS"""
        try:
            from crontab import CronTab

            cron = CronTab(user=True)
            status = {}

            for job in cron:
                if job.comment in ['receipts-daily-report', 'receipts-weekly-report']:
                    report_type = 'daily' if 'daily' in job.comment else 'weekly'
                    status[report_type] = {
                        'enabled': True,
                        'schedule': str(job.slices),
                        'command': job.command,
                        'valid': job.is_valid()
                    }

            return status

        except ImportError:
            return self._get_cron_status_fallback()
        except Exception as e:
            return {"error": str(e)}

    def _get_cron_status_fallback(self) -> Dict[str, Dict]:
        """Fallback cron status using crontab command"""
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode != 0:
                return {}

            status = {}

            for line in result.stdout.split('\n'):
                if 'receipts-daily-report' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        status['daily'] = {
                            'enabled': True,
                            'schedule': f"{parts[0]} {parts[1]} {parts[2]} {parts[3]} {parts[4]}",
                            'command': ' '.join(parts[5:]).split('#')[0].strip(),
                            'valid': True
                        }
                elif 'receipts-weekly-report' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        status['weekly'] = {
                            'enabled': True,
                            'schedule': f"{parts[0]} {parts[1]} {parts[2]} {parts[3]} {parts[4]}",
                            'command': ' '.join(parts[5:]).split('#')[0].strip(),
                            'valid': True
                        }

            return status

        except Exception as e:
            return {"error": str(e)}

    def _get_windows_status(self) -> Dict[str, Dict]:
        """Get Windows Task Scheduler status"""
        try:
            status = {}
            task_names = {
                'receipts-daily-report': 'daily',
                'receipts-weekly-report': 'weekly'
            }

            for task_name, report_type in task_names.items():
                result = subprocess.run(
                    ['schtasks', '/query', '/tn', task_name, '/fo', 'csv'],
                    capture_output=True, text=True
                )

                if result.returncode == 0:
                    # Parse CSV output to get task details
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:  # Header + data
                        status[report_type] = {
                            'enabled': True,
                            'schedule': 'Windows Task Scheduler',
                            'command': task_name,
                            'valid': True
                        }

            return status

        except Exception as e:
            return {"error": str(e)}

    def print_schedule_status(self) -> None:
        """Print a formatted table of current schedule status"""
        status = self.get_schedule_status()

        if "error" in status:
            console.print(f"❌ Error getting schedule status: {status['error']}", style="red")
            return

        if not status:
            console.print("ℹ️  No scheduled reports configured", style="yellow")
            return

        table = Table(title="📅 Scheduled Reports Status")
        table.add_column("Report Type", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Schedule", style="white")
        table.add_column("Command", style="dim")

        for report_type, details in status.items():
            status_icon = "✅ Enabled" if details.get('enabled') else "❌ Disabled"
            table.add_row(
                report_type.title(),
                status_icon,
                details.get('schedule', 'Unknown'),
                details.get('command', 'Unknown')[:50] + "..." if len(details.get('command', '')) > 50 else details.get('command', 'Unknown')
            )

        console.print(table)