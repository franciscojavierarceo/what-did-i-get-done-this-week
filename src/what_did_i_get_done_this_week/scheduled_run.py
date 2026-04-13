"""
Entry point for cron-scheduled report generation
"""

import sys
from pathlib import Path
from datetime import date, timedelta
import click
from rich.console import Console

from .config import load_config, get_env_config
from .core import WeeklyReviewGenerator
from .models import DateRange
from .scheduling.popup import TerminalReportDisplay
from .scheduling.browser_popup import BrowserReportPopup
from .scheduling.native_popup import show_native_popup, native_popup_available
from .scheduling.scheduler import ScheduleManager

console = Console()


def get_date_range(report_type: str) -> DateRange:
    """Get appropriate date range for the report type"""
    today = date.today()

    if report_type == 'daily':
        # Yesterday's report
        yesterday = today - timedelta(days=1)
        return DateRange(start=yesterday, end=yesterday)

    elif report_type == 'weekly':
        # Last week's report (previous Monday to Sunday)
        days_since_monday = today.weekday()  # 0 = Monday, 6 = Sunday
        last_monday = today - timedelta(days=days_since_monday + 7)
        last_sunday = last_monday + timedelta(days=6)
        return DateRange(start=last_monday, end=last_sunday)

    else:
        raise ValueError(f"Invalid report type: {report_type}")


def generate_report(config, date_range: DateRange, report_type: str) -> Path:
    """Generate a report and return the output path"""
    generator = WeeklyReviewGenerator(config)

    # Generate output filename
    if report_type == 'daily':
        filename = f"daily-{date_range.start.isoformat()}.md"
    else:
        filename = f"weekly-{date_range.start.isoformat()}-to-{date_range.end.isoformat()}.md"

    output_path = config.output_dir / filename

    console.print(f"📊 Generating {report_type} report...")
    console.print(f"   Period: {date_range.start} to {date_range.end}")
    console.print(f"   Output: {output_path}")

    try:
        # Generate the report
        activities = generator.get_activities(date_range)
        report_content = generator.generate_report(activities, date_range)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the report
        output_path.write_text(report_content)

        console.print("✅ Report generated successfully!", style="green")
        return output_path

    except Exception as e:
        console.print(f"❌ Failed to generate report: {e}", style="red")
        raise


@click.command()
@click.argument('report_type', type=click.Choice(['daily', 'weekly']))
@click.option('--no-popup', is_flag=True, help="Force terminal mode")
@click.option('--config-file', type=click.Path(exists=True), help="Custom config file path")
def main(report_type: str, no_popup: bool, config_file: str):
    """Entry point for cron-scheduled report generation"""

    try:
        # Load configuration
        if config_file:
            config = load_config(Path(config_file))
        else:
            try:
                config = load_config()
            except Exception:
                # Fallback to environment config for backward compatibility
                config = get_env_config()
                if not config:
                    console.print(
                        "❌ No configuration found. Please run: receipts setup",
                        style="red"
                    )
                    sys.exit(1)

        # Get date range for the report
        date_range = get_date_range(report_type)

        # Generate the report
        output_path = generate_report(config, date_range, report_type)

        # Read the generated report content
        report_content = output_path.read_text()

        console.print(f"\n📋 Report ready: {output_path}")

        # Show report and collect reflections
        if no_popup or not config.schedule.popup_enabled:
            console.print("💻 Using terminal interface...")
            terminal_display = TerminalReportDisplay()
            result = terminal_display.show_report_with_reflections(report_content, str(output_path))
        elif native_popup_available():
            result = show_native_popup(report_content, str(output_path), preferred_method="auto")
            if result is None:
                console.print("⏭️ Falling back to browser popup...")
                browser_popup = BrowserReportPopup(report_content, str(output_path))
                result = browser_popup.show()
                if result in [None, "timeout"]:
                    console.print("⏭️ Falling back to terminal interface...")
                    terminal_display = TerminalReportDisplay()
                    result = terminal_display.show_report_with_reflections(report_content, str(output_path))
        else:
            console.print("🌐 Opening browser popup interface...")
            browser_popup = BrowserReportPopup(report_content, str(output_path))
            result = browser_popup.show()
            if result in [None, "timeout"]:
                console.print("⏭️ Falling back to terminal interface...")
                terminal_display = TerminalReportDisplay()
                result = terminal_display.show_report_with_reflections(report_content, str(output_path))

        # Handle the result
        if result == "disable":
            console.print("\n🚫 Disabling scheduled reports...")
            scheduler = ScheduleManager()
            if scheduler.remove_all_schedules():
                # Update config
                config.schedule.daily_enabled = False
                config.schedule.weekly_enabled = False
                config.save()
                console.print("✅ Scheduled reports disabled", style="green")
            else:
                console.print("❌ Failed to disable scheduled reports", style="red")
                sys.exit(1)

        elif result == "saved":
            console.print("✅ Session completed with reflections saved", style="green")

        elif result == "skipped":
            console.print("⏭️ Session completed (reflections skipped)", style="yellow")

        else:
            console.print("ℹ️ Session completed", style="blue")

    except KeyboardInterrupt:
        console.print("\n⚠️ Interrupted by user", style="yellow")
        sys.exit(130)

    except Exception as e:
        console.print(f"\n❌ Scheduled run failed: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    main()