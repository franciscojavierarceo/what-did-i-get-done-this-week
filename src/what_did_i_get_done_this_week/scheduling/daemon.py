"""
Background daemon service for scheduling (fallback option)
"""

import time
import threading
from datetime import datetime, time as dt_time
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import load_config
from ..scheduled_run import main as run_scheduled_report


class ScheduleDaemon:
    """Background daemon for running scheduled reports (fallback when cron is not available)"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.running = False

    def start(self):
        """Start the daemon"""
        if self.running:
            return

        try:
            config = load_config()
        except Exception as e:
            print(f"Failed to load config: {e}")
            return

        # Add daily job if enabled
        if config.schedule.daily_enabled:
            hour, minute = map(int, config.schedule.daily_time.split(':'))
            trigger = CronTrigger(hour=hour, minute=minute)
            self.scheduler.add_job(
                self._run_daily_report,
                trigger=trigger,
                id='daily_report',
                replace_existing=True
            )

        # Add weekly job if enabled
        if config.schedule.weekly_enabled:
            hour, minute = map(int, config.schedule.weekly_time.split(':'))
            day_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            day_of_week = day_map.get(config.schedule.weekly_day.lower(), 0)
            trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
            self.scheduler.add_job(
                self._run_weekly_report,
                trigger=trigger,
                id='weekly_report',
                replace_existing=True
            )

        self.scheduler.start()
        self.running = True
        print("Schedule daemon started")

    def stop(self):
        """Stop the daemon"""
        if not self.running:
            return

        self.scheduler.shutdown(wait=False)
        self.running = False
        print("Schedule daemon stopped")

    def _run_daily_report(self):
        """Run daily report"""
        try:
            # This would call the scheduled_run main function
            # For now, just print a message
            print(f"Running daily report at {datetime.now()}")
            # TODO: Implement actual report execution
        except Exception as e:
            print(f"Daily report failed: {e}")

    def _run_weekly_report(self):
        """Run weekly report"""
        try:
            # This would call the scheduled_run main function
            # For now, just print a message
            print(f"Running weekly report at {datetime.now()}")
            # TODO: Implement actual report execution
        except Exception as e:
            print(f"Weekly report failed: {e}")


def run_daemon():
    """Run the daemon in the foreground"""
    daemon = ScheduleDaemon()
    daemon.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        daemon.stop()


if __name__ == "__main__":
    run_daemon()