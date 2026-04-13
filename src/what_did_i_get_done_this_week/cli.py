"""
Beautiful CLI interface for "What Did I Get Done This Week?"
"""

import click
import re
from datetime import date, timedelta
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich.tree import Tree
from rich import box
from pathlib import Path
import os

from .core import WeeklyReviewGenerator
from .config import load_config, setup_config
from .models import DateRange, OutputFormat
from .readers import read_report
from .formatters import MarkdownFormatter, HTMLFormatter, JSONFormatter
from .scheduling import ScheduleManager
from .scheduling.popup import TerminalReportDisplay
from .scheduling.browser_popup import BrowserReportPopup
from .scheduling.native_popup import show_native_popup, native_popup_available
from . import __version__

console = Console()

REFLECTION_QUESTIONS = [
    ("What could I have done better?", "### What could I have done better?"),
    ("What is important that I am missing?", "### What is important that I am missing?"),
    ("Am I doing work that is aligned with my goals?", "### Am I doing work that is aligned with my goals?"),
    ("How do I feel?", "### How do I feel?"),
]
REFLECTION_PLACEHOLDER = "*[Add your thoughts]*"


def print_banner():
    """Print a beautiful banner"""
    banner_content = "🎯 What Did I Get Done This Week?\nGot the receipts on your productivity! 🧾"
    banner_panel = Panel(
        banner_content,
        style="bold cyan",
        padding=(0, 1),
        expand=False
    )
    console.print(banner_panel)


def parse_timeframe(timeframe: str) -> Optional[DateRange]:
    """Parse timeframe string into DateRange"""
    today = date.today()

    if timeframe == 'today':
        return DateRange(start=today, end=today)

    elif timeframe == 'yesterday':
        yesterday = today - timedelta(days=1)
        return DateRange(start=yesterday, end=yesterday)

    elif timeframe == 'this-week':
        # Monday to today (or Sunday if today is Sunday)
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        # If it's Monday, show just Monday. Otherwise show Monday to today.
        end_date = today if today.weekday() != 0 else today
        return DateRange(start=monday, end=end_date)

    elif timeframe == 'last-week':
        # Last Monday to Sunday
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        last_monday = this_monday - timedelta(days=7)
        last_sunday = last_monday + timedelta(days=6)
        return DateRange(start=last_monday, end=last_sunday)

    elif timeframe == 'this-month':
        # First day of current month to today
        first_day = today.replace(day=1)
        return DateRange(start=first_day, end=today)

    elif timeframe == 'last-month':
        # First day to last day of previous month
        # Get first day of current month, then subtract 1 day to get last month
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        return DateRange(start=first_day_last_month, end=last_day_last_month)

    else:
        # Try to parse as MM-DD or MM-DD-YY
        try:
            # MM-DD format
            if len(timeframe) == 5 and timeframe[2] == '-':
                month, day = timeframe.split('-')
                target_date = date(today.year, int(month), int(day))
                # If the date is in the future, assume last year
                if target_date > today:
                    target_date = date(today.year - 1, int(month), int(day))
                return DateRange(start=target_date, end=target_date)

            # MM-DD-YY format
            elif len(timeframe) == 8 and timeframe[2] == '-' and timeframe[5] == '-':
                month, day, year = timeframe.split('-')
                # Convert YY to full year (assume 20XX)
                full_year = 2000 + int(year) if int(year) < 50 else 1900 + int(year)
                target_date = date(full_year, int(month), int(day))
                return DateRange(start=target_date, end=target_date)

        except (ValueError, IndexError):
            pass

    return None


def get_week_dates(start_date: str = None) -> DateRange:
    """Get Monday-Sunday date range for a given week (legacy function)"""
    if start_date:
        try:
            start = date.fromisoformat(start_date)
            # Ensure it's a Monday
            start = start - timedelta(days=start.weekday())
        except ValueError:
            console.print("❌ Invalid date format. Use YYYY-MM-DD", style="red")
            raise click.Abort()
    else:
        # Last week
        today = date.today()
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        start = last_monday

    end = start + timedelta(days=6)
    return DateRange(start=start, end=end)


@click.command()
@click.argument('timeframe', required=False, default='last-week')
@click.argument('sub_timeframe', required=False, default=None)
@click.option('--output', '-o', type=click.Path(), help='Output file (auto-generated if not specified)')
@click.option('--format', '-f', type=click.Choice(['markdown', 'html', 'json']), default='markdown', help='Output format')
@click.option('--no-calendar', is_flag=True, help='Skip calendar integration')
@click.option('--no-claude', is_flag=True, help='Skip Claude activity tracking')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode with preview')
@click.option('--display', '-d', is_flag=True, help='Display rendered report in CLI instead of saving to file')
@click.option('--no-display', is_flag=True, help='Skip displaying generated report (save to file only)')
@click.option('--force', is_flag=True, help='Force regeneration even if cached output exists')
@click.option('--reflect', '-r', is_flag=True, help='Prompt for reflections after generating report')
@click.option('--no-popup', is_flag=True, help='Force terminal interface for reflections (disable GUI popup)')
@click.version_option(version=__version__)
def cli(timeframe, sub_timeframe, output, format, no_calendar, no_claude, interactive, display, no_display, force, reflect, no_popup):
    """🎯 What Did I Get Done This Week? v0.3.0

    Got the receipts on your productivity! A beautiful CLI tool for tracking
    your daily and weekly accomplishments.

    \b
    Usage:
      receipts                 # Last week's receipts (default)
      receipts this-week       # This week so far
      receipts last-week       # Last week
      receipts this-month      # This month so far
      receipts last-month      # Last month (complete)
      receipts today          # Today's receipts
      receipts yesterday      # Yesterday's receipts
      receipts 03-25          # Specific date (MM-DD)
      receipts 03-25-24       # Specific date (MM-DD-YY)

    \b
    Render existing reports:
      receipts report.json --format html --display    # Show HTML in CLI
      receipts report.md --format markdown --display  # Show Markdown in CLI
      receipts report.json --format html --output presentation.html  # Save to file

    \b
    Generate and display:
      receipts last-week                              # Generate and show in CLI (default)
      receipts today --format json                   # Generate JSON and show (default)
      receipts this-week --no-display                # Generate only, skip display
      receipts last-week --display                   # Show cached report only

    \b
    Reflect:
      receipts reflect             # Reflect on last week's report (GUI popup)
      receipts reflect yesterday   # Reflect on yesterday's report (GUI popup)
      receipts reflect --no-popup  # Reflect using terminal interface
      receipts today reflect       # Reflect on today's report (GUI popup)

    \b
    Schedule:
      receipts schedule daily         # Setup daily reports at 9am for yesterday
      receipts schedule weekly        # Setup weekly reports at 9am Mondays for last week
      receipts schedule status        # Show current schedule status
      receipts schedule disable       # Disable all scheduled reports

    \b
    Manage:
      receipts list           # Show all generated reports
      receipts setup          # First-time configuration
      receipts status         # Check current setup
    """

    # Print banner once at the start
    print_banner()

    # Handle special commands first
    if timeframe == 'setup':
        setup_command()
        return
    elif timeframe == 'status':
        status_command()
        return
    elif timeframe == 'list':
        list_command()
        return
    elif timeframe == 'reflect':
        reflect_command(sub_timeframe, no_popup)
        return
    elif sub_timeframe == 'reflect':
        reflect_command(timeframe, no_popup)
        return
    elif timeframe == 'schedule':
        schedule_command(sub_timeframe)
        return
    elif timeframe == 'render':
        # For render command, we need to show usage since file path is required
        console.print("❌ [red]Missing file path for render command[/red]")
        console.print()
        console.print("💡 [yellow]Usage:[/yellow]")
        console.print("  receipts render <file_path> [--format FORMAT] [--output OUTPUT]")
        console.print()
        console.print("🎯 [cyan]Examples:[/cyan]")
        console.print("  receipts render reports/review-2024-W15.json --format html")
        console.print("  receipts render yesterday-2024-04-07.md --format json")
        console.print("  receipts render reports/weekly-summary.md --format html --output presentation.html")
        console.print("  receipts render weekly-summary.md --format markdown --display  # Show in CLI")
        console.print("  receipts render report.json --format html --force  # Force regeneration")
        raise click.Abort()
    elif timeframe and (Path(timeframe).exists() or '.' in timeframe):
        # If timeframe looks like a file path, treat it as render command
        render_command(timeframe, output, format, interactive, display, force)
        return

    # Parse timeframe and generate report
    date_range = parse_timeframe(timeframe)
    if not date_range:
        console.print(f"❌ Invalid timeframe: {timeframe}", style="red")
        console.print("💡 Use: today, yesterday, this-week, last-week, this-month, last-month, MM-DD, or MM-DD-YY", style="yellow")
        raise click.Abort()

    # Determine report type: daily, weekly, or monthly
    is_daily = date_range.start == date_range.end
    duration_days = (date_range.end - date_range.start).days + 1
    is_monthly = duration_days > 14  # More than 2 weeks, treat as monthly

    if is_daily:
        generate_daily_report(date_range, output, format, no_calendar, no_claude, interactive, display, no_display, reflect, force)
    elif is_monthly:
        generate_monthly_report(date_range, output, format, no_calendar, no_claude, interactive, display, no_display, timeframe, reflect, force)
    else:
        generate_weekly_report(date_range, output, format, no_calendar, no_claude, interactive, display, no_display, reflect, force)


def generate_daily_report(date_range: DateRange, output, format, no_calendar, no_claude, interactive, display: bool = False, no_display: bool = False, reflect: bool = False, force: bool = False):
    """Generate a daily review report"""

    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        console.print(f"❌ Configuration error: {e}", style="red")
        console.print("💡 Run: receipts setup", style="yellow")
        raise click.Abort()

    target_date = date_range.start
    date_name = "today" if target_date == date.today() else "yesterday" if target_date == date.today() - timedelta(days=1) else target_date.strftime("%Y-%m-%d")

    # For display mode, look for existing cached report files
    if display:
        reports_dir = Path(config.output_dir)

        # Try different possible filenames for this date
        possible_files = []
        if date_name == "today":
            possible_files.extend([
                reports_dir / f"today-{target_date}.{format}",
                reports_dir / f"daily-{target_date}.{format}"
            ])
        elif date_name == "yesterday":
            possible_files.extend([
                reports_dir / f"yesterday-{target_date}.{format}",
                reports_dir / f"daily-{target_date}.{format}"
            ])
        else:
            possible_files.append(reports_dir / f"daily-{target_date}.{format}")

        # Look for existing report
        existing_report = None
        for possible_file in possible_files:
            if possible_file.exists():
                existing_report = possible_file
                break

        if existing_report:
            console.print(f"📄 Found cached report: [bold]{existing_report}[/bold]")
            console.print(f"📺 Displaying {date_name}'s receipts for: [bold]{target_date}[/bold]")

            # Read and display the cached report
            try:
                cached_content = existing_report.read_text(encoding='utf-8')

                console.print()
                if format == 'markdown':
                    display_panel = Panel.fit(
                        f"📄 [bold cyan]{date_name.title()}'s Report:[/bold cyan] (Cached)\n"
                        f"🗓️  Date: [bold]{target_date}[/bold]",
                        title="📖 Cached Report",
                        border_style="yellow"
                    )
                    console.print(display_panel)
                    console.print()
                    console.print(Markdown(cached_content))

                elif format == 'json':
                    display_panel = Panel.fit(
                        f"📄 [bold cyan]{date_name.title()}'s Report:[/bold cyan] (Cached)\n"
                        f"🗓️  Date: [bold]{target_date}[/bold]",
                        title="📊 Cached Report (JSON)",
                        border_style="yellow"
                    )
                    console.print(display_panel)
                    console.print()
                    from rich.syntax import Syntax
                    syntax = Syntax(cached_content, "json", theme="monokai", line_numbers=True)
                    console.print(syntax)

                elif format == 'html':
                    display_panel = Panel.fit(
                        f"📄 [bold cyan]{date_name.title()}'s Report:[/bold cyan] (Cached)\n"
                        f"🗓️  Date: [bold]{target_date}[/bold]\n\n"
                        f"💡 [yellow]HTML is best viewed in a browser.[/yellow]",
                        title="🌐 Cached Report (HTML)",
                        border_style="yellow"
                    )
                    console.print(display_panel)
                    console.print()
                    preview = cached_content[:1000] + "\n..." if len(cached_content) > 1000 else cached_content
                    from rich.syntax import Syntax
                    syntax = Syntax(preview, "html", theme="monokai", line_numbers=True)
                    console.print(syntax)

                console.print()
                console.print("✨ [green]Cached report display complete![/green]")
                return

            except Exception as e:
                console.print(f"❌ [red]Could not read cached report:[/red] {e}")
                raise click.Abort()
        else:
            # No cached report found
            console.print(f"❌ [red]No cached {format} report found for {date_name} ({target_date})[/red]")
            console.print()
            console.print("💡 [yellow]Generate a report first:[/yellow]")
            console.print(f"  receipts {date_name} --format {format}")
            console.print(f"  receipts {date_name} --format {format} --output my-report.{format}")
            raise click.Abort()

    # File mode - continue with normal generation

    # Determine output path early for cache check
    if not output:
        reports_dir = Path(config.output_dir)
        reports_dir.mkdir(exist_ok=True)
        if date_name == "today":
            output = reports_dir / f"today-{target_date}.{format}"
        elif date_name == "yesterday":
            output = reports_dir / f"yesterday-{target_date}.{format}"
        else:
            output = reports_dir / f"daily-{target_date}.{format}"
    else:
        output = Path(output)

    # Check for cached report
    if not force and output.exists():
        console.print(f"⚡ [yellow]Using cached report:[/yellow] {output}")
        console.print(f"💡 [dim]Use --force to regenerate[/dim]")
        report = output.read_text(encoding='utf-8')
    else:
        console.print(f"📅 Generating {date_name}'s receipts for: [bold]{target_date}[/bold]")
        console.print(f"👤 GitHub user: [bold cyan]{config.github_username}[/bold cyan]")

        if interactive:
            if not click.confirm("🤔 Continue with these settings?"):
                raise click.Abort()

        # Initialize generator
        generator = WeeklyReviewGenerator(config)

        # Show progress with beautiful spinner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:

            # Fetch GitHub data
            task1 = progress.add_task(f"🔍 Fetching {date_name}'s GitHub activity...", total=None)
            contributions = generator.fetch_github_contributions(date_range)
            progress.update(task1, description="✅ GitHub activity fetched")

            task2 = progress.add_task(f"📝 Fetching {date_name}'s PRs and issues...", total=None)
            prs_issues = generator.fetch_prs_and_issues(date_range)
            progress.update(task2, description="✅ PRs and issues fetched")

            if config.enable_calendar:
                task3 = progress.add_task(f"📅 Fetching {date_name}'s meetings...", total=None)
                calendar_data = generator.fetch_calendar_events(date_range)
                progress.update(task3, description="✅ Calendar events fetched")
            else:
                calendar_data = None

            if config.enable_claude_tracking:
                task4 = progress.add_task(f"🤖 Analyzing {date_name}'s Claude activity...", total=None)
                claude_data = generator.estimate_claude_activity(date_range)
                progress.update(task4, description="✅ Claude activity analyzed")
            else:
                claude_data = None

            task5 = progress.add_task(f"📊 Generating {date_name}'s receipts...", total=None)
            report = generator.generate_report(
                date_range=date_range,
                contributions=contributions,
                prs_issues=prs_issues,
                calendar_data=calendar_data,
                claude_data=claude_data,
                output_format=format
            )
            progress.update(task5, description="✅ Receipts generated")

        # Save report
        output.write_text(report, encoding='utf-8')

    if display:
        # Display mode - show content in CLI
        console.print()

        if format == 'markdown':
            # Render markdown beautifully in CLI
            display_panel = Panel.fit(
                f"📄 [bold cyan]{date_name.title()}'s Report:[/bold cyan]\n"
                f"🗓️  Date: [bold]{target_date}[/bold]",
                title="📖 Generated Report",
                border_style="cyan"
            )
            console.print(display_panel)
            console.print()
            console.print(Markdown(report))

        elif format == 'json':
            # Show JSON with syntax highlighting
            display_panel = Panel.fit(
                f"📄 [bold cyan]{date_name.title()}'s Report:[/bold cyan]\n"
                f"🗓️  Date: [bold]{target_date}[/bold]",
                title="📊 Generated Report (JSON)",
                border_style="cyan"
            )
            console.print(display_panel)
            console.print()

            # Use Rich's JSON syntax highlighting
            from rich.syntax import Syntax
            syntax = Syntax(report, "json", theme="monokai", line_numbers=True)
            console.print(syntax)

        elif format == 'html':
            # For HTML, show a sample and suggest saving to file
            display_panel = Panel.fit(
                f"📄 [bold cyan]{date_name.title()}'s Report:[/bold cyan]\n"
                f"🗓️  Date: [bold]{target_date}[/bold]\n\n"
                f"💡 [yellow]HTML is best viewed in a browser.[/yellow]\n"
                f"Consider saving with [bold]--output filename.html[/bold].",
                title="🌐 Generated Report (HTML)",
                border_style="cyan"
            )
            console.print(display_panel)
            console.print()

            # Show first part of HTML
            preview = report[:1000] + "\n..." if len(report) > 1000 else report
            from rich.syntax import Syntax
            syntax = Syntax(preview, "html", theme="monokai", line_numbers=True)
            console.print(syntax)

        console.print()
        console.print("✨ [green]Report display complete![/green]")

    else:
        # Show success message
        console.print()
        success_panel = Panel.fit(
            f"✅ [bold green]{date_name.title()}'s receipts generated![/bold green]\n\n"
            f"📁 File: [bold]{output}[/bold]\n"
            f"📊 Format: [bold]{format.upper()}[/bold]\n"
            f"🗓️  Date: [bold]{target_date}[/bold]",
            title="🧾 Got Your Receipts!",
            border_style="green"
        )
        console.print(success_panel)

        # Handle --reflect flag
        if reflect:
            if format == 'markdown':
                handle_reflections(output, config, no_popup)
            else:
                console.print("⚠️  [yellow]Reflections only work with markdown format. Use --format markdown --reflect[/yellow]")

        # Auto-display by default (unless --no-display is used)
        if not no_display:
            console.print()
            console.print("📺 [bold cyan]Displaying generated report:[/bold cyan]")

            if format == 'markdown':
                display_panel = Panel.fit(
                    f"📄 [bold cyan]{date_name.title()}'s Report:[/bold cyan]\n"
                    f"🗓️  Date: [bold]{target_date}[/bold]",
                    title="📖 Generated Report",
                    border_style="cyan"
                )
                console.print(display_panel)
                console.print()
                console.print(Markdown(report))

            elif format == 'json':
                display_panel = Panel.fit(
                    f"📄 [bold cyan]{date_name.title()}'s Report:[/bold cyan]\n"
                    f"🗓️  Date: [bold]{target_date}[/bold]",
                    title="📊 Generated Report (JSON)",
                    border_style="cyan"
                )
                console.print(display_panel)
                console.print()
                from rich.syntax import Syntax
                syntax = Syntax(report, "json", theme="monokai", line_numbers=True)
                console.print(syntax)

            elif format == 'html':
                display_panel = Panel.fit(
                    f"📄 [bold cyan]{date_name.title()}'s Report:[/bold cyan]\n"
                    f"🗓️  Date: [bold]{target_date}[/bold]\n\n"
                    f"💡 [yellow]HTML is best viewed in a browser.[/yellow]\n"
                    f"File saved to: [bold]{output}[/bold]",
                    title="🌐 Generated Report (HTML)",
                    border_style="cyan"
                )
                console.print(display_panel)
                console.print()
                preview = report[:1000] + "\n..." if len(report) > 1000 else report
                from rich.syntax import Syntax
                syntax = Syntax(preview, "html", theme="monokai", line_numbers=True)
                console.print(syntax)

        # Legacy interactive preview (kept for compatibility)
        elif interactive and format == 'markdown':
            console.print("\n📖 [bold]Preview:[/bold]")
            preview = report[:1000] + "..." if len(report) > 1000 else report
            console.print(Markdown(preview))

        # Offer to open file
        if interactive:
            if click.confirm("🔍 Open the report file?"):
                os.system(f"code '{output}'" if os.system("which code > /dev/null 2>&1") == 0 else f"cat '{output}'")


def generate_weekly_report(date_range: DateRange, output, format, no_calendar, no_claude, interactive, display: bool = False, no_display: bool = False, reflect: bool = False, force: bool = False):
    """Generate a weekly review report"""

    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        console.print(f"❌ Configuration error: {e}", style="red")
        console.print("💡 Run: receipts setup", style="yellow")
        raise click.Abort()

    # For display mode, look for existing cached report files
    if display:
        reports_dir = Path(config.output_dir)
        week_num = date_range.start.isocalendar()[1]
        year = date_range.start.year

        # Try different possible filenames for this week
        today = date.today()
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)

        possible_files = []
        if date_range.start == this_monday and date_range.end >= today:
            # This week (partial)
            possible_files.append(reports_dir / f"this-week-{year}-W{week_num:02d}.{format}")
        else:
            # Complete week or last week
            possible_files.append(reports_dir / f"review-{year}-W{week_num:02d}.{format}")

        # Also try generic weekly naming
        possible_files.append(reports_dir / f"weekly-{year}-W{week_num:02d}.{format}")

        # Look for existing report
        existing_report = None
        for possible_file in possible_files:
            if possible_file.exists():
                existing_report = possible_file
                break

        if existing_report:
            console.print(f"📄 Found cached report: [bold]{existing_report}[/bold]")
            console.print(f"📺 Displaying weekly report for: [bold]{date_range.start}[/bold] to [bold]{date_range.end}[/bold]")

            # Read and display the cached report
            try:
                cached_content = existing_report.read_text(encoding='utf-8')

                console.print()
                if format == 'markdown':
                    display_panel = Panel.fit(
                        f"📄 [bold cyan]Weekly Report:[/bold cyan] (Cached)\n"
                        f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]",
                        title="📖 Cached Report",
                        border_style="yellow"
                    )
                    console.print(display_panel)
                    console.print()
                    console.print(Markdown(cached_content))

                elif format == 'json':
                    display_panel = Panel.fit(
                        f"📄 [bold cyan]Weekly Report:[/bold cyan] (Cached)\n"
                        f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]",
                        title="📊 Cached Report (JSON)",
                        border_style="yellow"
                    )
                    console.print(display_panel)
                    console.print()
                    from rich.syntax import Syntax
                    syntax = Syntax(cached_content, "json", theme="monokai", line_numbers=True)
                    console.print(syntax)

                elif format == 'html':
                    display_panel = Panel.fit(
                        f"📄 [bold cyan]Weekly Report:[/bold cyan] (Cached)\n"
                        f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]\n\n"
                        f"💡 [yellow]HTML is best viewed in a browser.[/yellow]",
                        title="🌐 Cached Report (HTML)",
                        border_style="yellow"
                    )
                    console.print(display_panel)
                    console.print()
                    preview = cached_content[:1000] + "\n..." if len(cached_content) > 1000 else cached_content
                    from rich.syntax import Syntax
                    syntax = Syntax(preview, "html", theme="monokai", line_numbers=True)
                    console.print(syntax)

                console.print()
                console.print("✨ [green]Cached report display complete![/green]")
                return

            except Exception as e:
                console.print(f"❌ [red]Could not read cached report:[/red] {e}")
                raise click.Abort()
        else:
            # No cached report found
            console.print(f"❌ [red]No cached {format} report found for week {year}-W{week_num:02d}[/red]")
            console.print()
            console.print("💡 [yellow]Generate a report first:[/yellow]")
            console.print(f"  receipts last-week --format {format}")
            console.print(f"  receipts this-week --format {format}")
            raise click.Abort()

    # File mode - continue with normal generation
    # Override config with command line options
    if no_calendar:
        config.enable_calendar = False
    if no_claude:
        config.enable_claude_tracking = False

    # Determine output path early for cache check
    if not output:
        week_num = date_range.start.isocalendar()[1]
        year = date_range.start.year
        reports_dir = Path(config.output_dir)
        reports_dir.mkdir(exist_ok=True)

        # Different naming based on week type
        today = date.today()
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)

        if date_range.start == this_monday and date_range.end >= today:
            output = reports_dir / f"this-week-{year}-W{week_num:02d}.{format}"
        else:
            output = reports_dir / f"review-{year}-W{week_num:02d}.{format}"
    else:
        output = Path(output)

    # Check for cached report
    if not force and output.exists():
        console.print(f"⚡ [yellow]Using cached report:[/yellow] {output}")
        console.print(f"💡 [dim]Use --force to regenerate[/dim]")
        report = output.read_text(encoding='utf-8')
    else:
        console.print(f"📅 Generating report for: [bold]{date_range.start}[/bold] to [bold]{date_range.end}[/bold]")
        console.print(f"👤 GitHub user: [bold cyan]{config.github_username}[/bold cyan]")

        if interactive:
            if not click.confirm("🤔 Continue with these settings?"):
                raise click.Abort()

        # Initialize generator
        generator = WeeklyReviewGenerator(config)

        # Show progress with beautiful spinner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:

            # Fetch GitHub data
            task1 = progress.add_task("🔍 Fetching GitHub contributions...", total=None)
            contributions = generator.fetch_github_contributions(date_range)
            progress.update(task1, description="✅ GitHub contributions fetched")

            task2 = progress.add_task("📝 Fetching PRs and issues...", total=None)
            prs_issues = generator.fetch_prs_and_issues(date_range)
            progress.update(task2, description="✅ PRs and issues fetched")

            if config.enable_calendar:
                task3 = progress.add_task("📅 Fetching calendar events...", total=None)
                calendar_data = generator.fetch_calendar_events(date_range)
                progress.update(task3, description="✅ Calendar events fetched")
            else:
                calendar_data = None

            if config.enable_claude_tracking:
                task4 = progress.add_task("🤖 Analyzing Claude activity...", total=None)
                claude_data = generator.estimate_claude_activity(date_range)
                progress.update(task4, description="✅ Claude activity analyzed")
            else:
                claude_data = None

            task5 = progress.add_task("📊 Generating report...", total=None)
            report = generator.generate_report(
                date_range=date_range,
                contributions=contributions,
                prs_issues=prs_issues,
                calendar_data=calendar_data,
                claude_data=claude_data,
                output_format=format
            )
            progress.update(task5, description="✅ Report generated")

        # Save report
        output.write_text(report, encoding='utf-8')

    if display:
        # Display mode - show content in CLI
        console.print()

        if format == 'markdown':
            # Render markdown beautifully in CLI
            display_panel = Panel.fit(
                f"📄 [bold cyan]Weekly Report:[/bold cyan]\n"
                f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]",
                title="📖 Generated Report",
                border_style="cyan"
            )
            console.print(display_panel)
            console.print()
            console.print(Markdown(report))

        elif format == 'json':
            # Show JSON with syntax highlighting
            display_panel = Panel.fit(
                f"📄 [bold cyan]Weekly Report:[/bold cyan]\n"
                f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]",
                title="📊 Generated Report (JSON)",
                border_style="cyan"
            )
            console.print(display_panel)
            console.print()

            # Use Rich's JSON syntax highlighting
            from rich.syntax import Syntax
            syntax = Syntax(report, "json", theme="monokai", line_numbers=True)
            console.print(syntax)

        elif format == 'html':
            # For HTML, show a sample and suggest saving to file
            display_panel = Panel.fit(
                f"📄 [bold cyan]Weekly Report:[/bold cyan]\n"
                f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]\n\n"
                f"💡 [yellow]HTML is best viewed in a browser.[/yellow]\n"
                f"Consider saving with [bold]--output filename.html[/bold].",
                title="🌐 Generated Report (HTML)",
                border_style="cyan"
            )
            console.print(display_panel)
            console.print()

            # Show first part of HTML
            preview = report[:1000] + "\n..." if len(report) > 1000 else report
            from rich.syntax import Syntax
            syntax = Syntax(preview, "html", theme="monokai", line_numbers=True)
            console.print(syntax)

        console.print()
        console.print("✨ [green]Report display complete![/green]")

    else:
        # Show success message
        console.print()
        success_panel = Panel.fit(
            f"✅ [bold green]Report generated successfully![/bold green]\n\n"
            f"📁 File: [bold]{output}[/bold]\n"
            f"📊 Format: [bold]{format.upper()}[/bold]\n"
            f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]",
            title="🎉 Success",
            border_style="green"
        )
        console.print(success_panel)

        # Handle --reflect flag
        if reflect:
            if format == 'markdown':
                handle_reflections(output, config, no_popup)
            else:
                console.print("⚠️  [yellow]Reflections only work with markdown format. Use --format markdown --reflect[/yellow]")

        # Auto-display by default (unless --no-display is used)
        if not no_display:
            console.print()
            console.print("📺 [bold cyan]Displaying generated report:[/bold cyan]")

            if format == 'markdown':
                display_panel = Panel.fit(
                    f"📄 [bold cyan]Weekly Report:[/bold cyan]\n"
                    f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]",
                    title="📖 Generated Report",
                    border_style="cyan"
                )
                console.print(display_panel)
                console.print()
                console.print(Markdown(report))

            elif format == 'json':
                display_panel = Panel.fit(
                    f"📄 [bold cyan]Weekly Report:[/bold cyan]\n"
                    f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]",
                    title="📊 Generated Report (JSON)",
                    border_style="cyan"
                )
                console.print(display_panel)
                console.print()
                from rich.syntax import Syntax
                syntax = Syntax(report, "json", theme="monokai", line_numbers=True)
                console.print(syntax)

            elif format == 'html':
                display_panel = Panel.fit(
                    f"📄 [bold cyan]Weekly Report:[/bold cyan]\n"
                    f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]\n\n"
                    f"💡 [yellow]HTML is best viewed in a browser.[/yellow]\n"
                    f"File saved to: [bold]{output}[/bold]",
                    title="🌐 Generated Report (HTML)",
                    border_style="cyan"
                )
                console.print(display_panel)
                console.print()
                preview = report[:1000] + "\n..." if len(report) > 1000 else report
                from rich.syntax import Syntax
                syntax = Syntax(preview, "html", theme="monokai", line_numbers=True)
                console.print(syntax)

        # Legacy interactive preview (kept for compatibility)
        elif interactive and format == 'markdown':
            console.print("\n📖 [bold]Preview:[/bold]")
            preview = report[:1000] + "..." if len(report) > 1000 else report
            console.print(Markdown(preview))

        # Offer to open file
        if interactive:
            if click.confirm("🔍 Open the report file?"):
                os.system(f"code '{output}'" if os.system("which code > /dev/null 2>&1") == 0 else f"cat '{output}'")


def generate_monthly_report(date_range: DateRange, output, format, no_calendar, no_claude, interactive, display: bool = False, no_display: bool = False, timeframe: str = "", reflect: bool = False, force: bool = False):
    """Generate a monthly review report"""

    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        console.print(f"❌ Configuration error: {e}", style="red")
        console.print("💡 Run: receipts setup", style="yellow")
        raise click.Abort()

    # Override config with command line options
    if no_calendar:
        config.enable_calendar = False
    if no_claude:
        config.enable_claude_tracking = False

    # Determine output path early for cache check
    if not output:
        month = date_range.start.month
        year = date_range.start.year
        reports_dir = Path(config.output_dir)
        reports_dir.mkdir(exist_ok=True)

        today = date.today()
        first_day_this_month = today.replace(day=1)

        if date_range.start == first_day_this_month:
            output = reports_dir / f"this-month-{year}-{month:02d}.{format}"
        else:
            output = reports_dir / f"monthly-{year}-{month:02d}.{format}"
    else:
        output = Path(output)

    # Check for cached report
    if not force and output.exists():
        console.print(f"⚡ [yellow]Using cached report:[/yellow] {output}")
        console.print(f"💡 [dim]Use --force to regenerate[/dim]")
        report = output.read_text(encoding='utf-8')
    else:
        console.print(f"📅 Generating monthly report for: [bold]{date_range.start}[/bold] to [bold]{date_range.end}[/bold]")
        console.print(f"👤 GitHub user: [bold cyan]{config.github_username}[/bold cyan]")

        if interactive:
            if not click.confirm("🤔 Continue with these settings?"):
                raise click.Abort()

        # Initialize generator
        generator = WeeklyReviewGenerator(config)

        # Show progress with beautiful spinner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:

            # Fetch GitHub data
            task1 = progress.add_task("🔍 Fetching GitHub contributions...", total=None)
            contributions = generator.fetch_github_contributions(date_range)
            progress.update(task1, description="✅ GitHub contributions fetched")

            task2 = progress.add_task("📝 Fetching PRs and issues...", total=None)
            prs_issues = generator.fetch_prs_and_issues(date_range)
            progress.update(task2, description="✅ PRs and issues fetched")

            if config.enable_calendar:
                task3 = progress.add_task("📅 Fetching calendar events...", total=None)
                calendar_data = generator.fetch_calendar_events(date_range)
                progress.update(task3, description="✅ Calendar events fetched")
            else:
                calendar_data = None

            if config.enable_claude_tracking:
                task4 = progress.add_task("🤖 Analyzing Claude activity...", total=None)
                claude_data = generator.estimate_claude_activity(date_range)
                progress.update(task4, description="✅ Claude activity analyzed")
            else:
                claude_data = None

            task5 = progress.add_task("📊 Generating monthly report...", total=None)
            report = generator.generate_report(
                date_range=date_range,
                contributions=contributions,
                prs_issues=prs_issues,
                calendar_data=calendar_data,
                claude_data=claude_data,
                output_format=format
            )
            progress.update(task5, description="✅ Monthly report generated")

        # Save report
        output.write_text(report, encoding='utf-8')

    if display:
        # Display mode - show content in CLI
        console.print()

        if format == 'markdown':
            # Render markdown beautifully in CLI
            display_panel = Panel.fit(
                f"📄 [bold cyan]Monthly Report:[/bold cyan]\n"
                f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]",
                title="📖 Generated Report",
                border_style="cyan"
            )
            console.print(display_panel)
            console.print()
            console.print(Markdown(report))

        elif format == 'json':
            # Show JSON with syntax highlighting
            display_panel = Panel.fit(
                f"📄 [bold cyan]Monthly Report:[/bold cyan]\n"
                f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]",
                title="📊 Generated Report (JSON)",
                border_style="cyan"
            )
            console.print(display_panel)
            console.print()

            # Use Rich's JSON syntax highlighting
            from rich.syntax import Syntax
            syntax = Syntax(report, "json", theme="monokai", line_numbers=True)
            console.print(syntax)

        elif format == 'html':
            # For HTML, show a sample and suggest saving to file
            display_panel = Panel.fit(
                f"📄 [bold cyan]Monthly Report:[/bold cyan]\n"
                f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]\n\n"
                f"💡 [yellow]HTML is best viewed in a browser.[/yellow]\n"
                f"Consider saving with [bold]--output filename.html[/bold].",
                title="🌐 Generated Report (HTML)",
                border_style="cyan"
            )
            console.print(display_panel)
            console.print()

            # Show first part of HTML
            preview = report[:1000] + "\n..." if len(report) > 1000 else report
            from rich.syntax import Syntax
            syntax = Syntax(preview, "html", theme="monokai", line_numbers=True)
            console.print(syntax)

        console.print()
        console.print("✨ [green]Report display complete![/green]")

    else:
        # Show success message
        console.print()
        success_panel = Panel.fit(
            f"✅ [bold green]Monthly report generated successfully![/bold green]\n\n"
            f"📁 File: [bold]{output}[/bold]\n"
            f"📊 Format: [bold]{format.upper()}[/bold]\n"
            f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]",
            title="🎉 Success",
            border_style="green"
        )
        console.print(success_panel)

        # Handle --reflect flag
        if reflect:
            if format == 'markdown':
                handle_reflections(output, config, no_popup)
            else:
                console.print("⚠️  [yellow]Reflections only work with markdown format. Use --format markdown --reflect[/yellow]")

        # Auto-display by default (unless --no-display is used)
        if not no_display:
            console.print()
            console.print("📺 [bold cyan]Displaying generated report:[/bold cyan]")

            if format == 'markdown':
                display_panel = Panel.fit(
                    f"📄 [bold cyan]Monthly Report:[/bold cyan]\n"
                    f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]",
                    title="📖 Generated Report",
                    border_style="cyan"
                )
                console.print(display_panel)
                console.print()
                console.print(Markdown(report))

            elif format == 'json':
                display_panel = Panel.fit(
                    f"📄 [bold cyan]Monthly Report:[/bold cyan]\n"
                    f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]",
                    title="📊 Generated Report (JSON)",
                    border_style="cyan"
                )
                console.print(display_panel)
                console.print()
                from rich.syntax import Syntax
                syntax = Syntax(report, "json", theme="monokai", line_numbers=True)
                console.print(syntax)

            elif format == 'html':
                display_panel = Panel.fit(
                    f"📄 [bold cyan]Monthly Report:[/bold cyan]\n"
                    f"🗓️  Period: [bold]{date_range.start} to {date_range.end}[/bold]\n\n"
                    f"💡 [yellow]HTML is best viewed in a browser.[/yellow]\n"
                    f"File saved to: [bold]{output}[/bold]",
                    title="🌐 Generated Report (HTML)",
                    border_style="cyan"
                )
                console.print(display_panel)
                console.print()
                preview = report[:1000] + "\n..." if len(report) > 1000 else report
                from rich.syntax import Syntax
                syntax = Syntax(preview, "html", theme="monokai", line_numbers=True)
                console.print(syntax)

        # Legacy interactive preview (kept for compatibility)
        elif interactive and format == 'markdown':
            console.print("\n📖 [bold]Preview:[/bold]")
            preview = report[:800] + "..." if len(report) > 800 else report
            console.print(Markdown(preview))

        # Offer to open file
        if interactive:
            if click.confirm("🔍 Open the report file?"):
                os.system(f"code '{output}'" if os.system("which code > /dev/null 2>&1") == 0 else f"cat '{output}'")


def find_report_file(timeframe_str, config):
    """Find an existing report file for the given timeframe"""
    date_range = parse_timeframe(timeframe_str)
    if not date_range:
        return None

    reports_dir = Path(config.output_dir)
    if not reports_dir.exists():
        return None

    is_daily = date_range.start == date_range.end
    duration_days = (date_range.end - date_range.start).days + 1
    is_monthly = duration_days > 14

    possible_files = []

    if is_daily:
        target_date = date_range.start
        today = date.today()
        date_name = "today" if target_date == today else "yesterday" if target_date == today - timedelta(days=1) else target_date.strftime("%Y-%m-%d")
        for ext in ['markdown', 'md']:
            if date_name == "today":
                possible_files.append(reports_dir / f"today-{target_date}.{ext}")
            elif date_name == "yesterday":
                possible_files.append(reports_dir / f"yesterday-{target_date}.{ext}")
            possible_files.append(reports_dir / f"daily-{target_date}.{ext}")
    elif is_monthly:
        month = date_range.start.month
        year = date_range.start.year
        today = date.today()
        first_day_this_month = today.replace(day=1)
        for ext in ['markdown', 'md']:
            if date_range.start == first_day_this_month:
                possible_files.append(reports_dir / f"this-month-{year}-{month:02d}.{ext}")
            possible_files.append(reports_dir / f"monthly-{year}-{month:02d}.{ext}")
    else:
        week_num = date_range.start.isocalendar()[1]
        year = date_range.start.year
        today = date.today()
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        for ext in ['markdown', 'md']:
            if date_range.start == this_monday and date_range.end >= today:
                possible_files.append(reports_dir / f"this-week-{year}-W{week_num:02d}.{ext}")
            possible_files.append(reports_dir / f"review-{year}-W{week_num:02d}.{ext}")
            possible_files.append(reports_dir / f"weekly-{year}-W{week_num:02d}.{ext}")

    for f in possible_files:
        if f.exists():
            return f

    # Fallback: most recently modified markdown file in reports dir
    md_files = list(reports_dir.glob("*.markdown")) + list(reports_dir.glob("*.md"))
    if md_files:
        return max(md_files, key=lambda p: p.stat().st_mtime)

    return None


def handle_reflections(report_path, config, no_popup=False):
    """Handle reflections using either popup or terminal interface"""
    try:
        report_path = Path(report_path)
        report_content = report_path.read_text(encoding='utf-8')
    except Exception as e:
        console.print(f"❌ Failed to read report: {e}", style="red")
        return

    # Determine which interface to use
    if no_popup:
        # User explicitly wants terminal mode
        console.print("💻 Using terminal interface...")
        terminal_display = TerminalReportDisplay()
        result = terminal_display.show_report_with_reflections(report_content, str(report_path))
    elif config.schedule.popup_enabled:
        # Try native popup with automatic fallback chain
        if native_popup_available():
            try:
                result = show_native_popup(report_content, str(report_path), preferred_method="auto")

                # If native popup failed (not user-cancelled), fall back to browser popup
                if result is None:
                    console.print("⏭️ Falling back to browser popup...")
                    browser_popup = BrowserReportPopup(report_content, str(report_path))
                    result = browser_popup.show()

                    # If browser also failed, fall back to terminal
                    if result in [None, "timeout"]:
                        console.print("⏭️ Falling back to terminal interface...")
                        terminal_display = TerminalReportDisplay()
                        result = terminal_display.show_report_with_reflections(report_content, str(report_path))
            except Exception as e:
                console.print(f"❌ Native popup failed: {e}", style="yellow")
                console.print("⏭️ Falling back to browser popup...")
                try:
                    browser_popup = BrowserReportPopup(report_content, str(report_path))
                    result = browser_popup.show()

                    if result in [None, "timeout"]:
                        console.print("⏭️ Falling back to terminal interface...")
                        terminal_display = TerminalReportDisplay()
                        result = terminal_display.show_report_with_reflections(report_content, str(report_path))
                except Exception as e2:
                    console.print(f"❌ Browser popup failed: {e2}", style="yellow")
                    console.print("⏭️ Falling back to terminal interface...")
                    terminal_display = TerminalReportDisplay()
                    result = terminal_display.show_report_with_reflections(report_content, str(report_path))
        else:
            # Native popup not available, try browser popup
            console.print("🌐 Opening browser popup interface...")
            try:
                browser_popup = BrowserReportPopup(report_content, str(report_path))
                result = browser_popup.show()

                # If browser popup failed or timed out, fall back to terminal
                if result in [None, "timeout"]:
                    console.print("⏭️ Falling back to terminal interface...")
                    terminal_display = TerminalReportDisplay()
                    result = terminal_display.show_report_with_reflections(report_content, str(report_path))
            except Exception as e:
                console.print(f"❌ Browser popup failed: {e}", style="yellow")
                console.print("⏭️ Falling back to terminal interface...")
                terminal_display = TerminalReportDisplay()
                result = terminal_display.show_report_with_reflections(report_content, str(report_path))
    else:
        # Popup disabled in config, use terminal
        console.print("💻 Using terminal interface...")
        terminal_display = TerminalReportDisplay()
        result = terminal_display.show_report_with_reflections(report_content, str(report_path))

    # Handle the result
    if result == "saved":
        console.print("✅ Reflections saved successfully!", style="green")
    elif result == "skipped":
        console.print("⏭️ Reflections skipped", style="yellow")
    elif result == "cancelled":
        console.print("🚪 Window closed", style="dim")
    elif result == "disable":
        # Only disable if there are actually schedules to disable
        if config.schedule.daily_enabled or config.schedule.weekly_enabled:
            console.print("🚫 Disabling scheduled reports...")
            scheduler = ScheduleManager()
            if scheduler.remove_all_schedules():
                config.schedule.daily_enabled = False
                config.schedule.weekly_enabled = False
                config.save()
                console.print("✅ Scheduled reports disabled", style="green")
            else:
                console.print("❌ Failed to disable scheduled reports", style="red")
        else:
            console.print("ℹ️ No scheduled reports were enabled", style="blue")
    elif result == "error":
        console.print("❌ Failed to save reflections", style="red")
    else:
        console.print("ℹ️ Reflection session completed", style="blue")


def fill_reflections(report_path):
    """Legacy function for backward compatibility - now uses terminal interface only"""
    report_path = Path(report_path)
    content = report_path.read_text(encoding='utf-8')

    has_placeholders = REFLECTION_PLACEHOLDER in content
    if not has_placeholders:
        if not click.confirm("📝 Reflections already filled. Overwrite existing reflections?"):
            console.print("⏭️  Skipping reflections.")
            return

    console.print()
    console.print(Panel.fit(
        "📝 [bold cyan]Time to reflect![/bold cyan]\n"
        "Answer each question below (press Enter to skip).",
        title="🎯 Reflections",
        border_style="cyan"
    ))
    console.print()

    for question, heading in REFLECTION_QUESTIONS:
        answer = click.prompt(f"💭 {question}", default="", show_default=False)
        answer = answer.strip()

        if not answer:
            continue

        if has_placeholders:
            # Replace the placeholder after this heading
            pattern = re.escape(heading) + r'\n' + re.escape(REFLECTION_PLACEHOLDER)
            replacement = heading + '\n' + answer
            content = re.sub(pattern, replacement, content)
        else:
            # Overwrite existing content after the heading (up to next heading or section break)
            pattern = re.escape(heading) + r'\n(.+?)(?=\n###|\n---|\n##|\Z)'
            replacement = heading + '\n' + answer
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    report_path.write_text(content, encoding='utf-8')
    console.print()
    console.print(f"✅ [bold green]Reflections saved to:[/bold green] {report_path}")


def reflect_command(sub_timeframe, no_popup=False):
    """Handle the 'receipts reflect' command"""
    try:
        config = load_config()
    except Exception as e:
        console.print(f"❌ Configuration error: {e}", style="red")
        console.print("💡 Run: receipts setup", style="yellow")
        raise click.Abort()

    timeframe_str = sub_timeframe or 'last-week'
    report_path = find_report_file(timeframe_str, config)

    if not report_path:
        console.print(f"❌ [red]No report found for '{timeframe_str}'[/red]")
        console.print()
        console.print("💡 [yellow]Generate a report first:[/yellow]")
        console.print(f"  receipts {timeframe_str}")
        raise click.Abort()

    console.print(f"📄 Found report: [bold]{report_path}[/bold]")
    console.print(f"🤔 Opening reflection interface...")

    # Use the new unified reflection handler
    handle_reflections(report_path, config, no_popup)


def list_command():
    """List all generated reports"""
    try:
        config = load_config()
    except Exception as e:
        console.print(f"❌ Configuration error: {e}", style="red")
        console.print("💡 Run: receipts setup", style="yellow")
        raise click.Abort()

    reports_dir = Path(config.output_dir)
    if not reports_dir.exists():
        console.print("📂 [yellow]No reports directory found.[/yellow]")
        console.print("💡 Generate your first report: [bold cyan]receipts today[/bold cyan]")
        return

    report_files = sorted(
        [f for f in reports_dir.iterdir() if f.is_file() and f.suffix in ('.markdown', '.md', '.html', '.json')],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not report_files:
        console.print("📂 [yellow]No reports found.[/yellow]")
        console.print("💡 Generate your first report: [bold cyan]receipts today[/bold cyan]")
        return

    table = Table(title="🧾 Your Receipts", box=box.ROUNDED)
    table.add_column("#", style="dim", width=3)
    table.add_column("Report", style="cyan", no_wrap=True)
    table.add_column("Format", style="yellow", width=8)
    table.add_column("Size", style="green", justify="right", width=8)
    table.add_column("Modified", style="magenta", no_wrap=True, width=12)
    table.add_column("Refl?", style="white", width=5)

    from datetime import datetime

    for i, f in enumerate(report_files, 1):
        stat = f.stat()
        size = stat.st_size
        if size >= 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} B"

        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%b %d %H:%M")

        ext = f.suffix.lstrip('.')
        fmt = {'markdown': 'md', 'md': 'md', 'html': 'html', 'json': 'json'}.get(ext, ext)

        # Check if reflections are filled (only for markdown files)
        reflected = ""
        if ext in ('markdown', 'md'):
            content = f.read_text(encoding='utf-8')
            if REFLECTION_PLACEHOLDER in content:
                reflected = "—"
            elif "## 🎯 Weekly Reflection" in content or "## 🎯" in content:
                reflected = "✅"

        table.add_row(str(i), f.name, fmt, size_str, modified, reflected)

    console.print(table)
    console.print(f"\n📁 [dim]{reports_dir}[/dim]")


def setup_command():
    """Interactive setup and configuration"""

    console.print("🚀 Welcome! Let's set up your weekly review system.\n")

    try:
        config = setup_config()
        console.print("\n✅ [bold green]Setup completed successfully![/bold green]")
        console.print(f"📁 Configuration saved to: [bold]{config.config_file}[/bold]")

        console.print("\n🎯 [bold]Next steps:[/bold]")
        console.print("• Run: [bold cyan]receipts[/bold cyan] (for last week)")
        console.print("• Or: [bold cyan]receipts today[/bold cyan]")
        console.print("• Or: [bold cyan]receipts --interactive[/bold cyan]")

    except Exception as e:
        console.print(f"\n❌ Setup failed: {e}", style="red")
        raise click.Abort()


def status_command():
    """Show current configuration and system status"""

    try:
        config = load_config()

        # Create status table
        table = Table(title="🔧 Configuration Status", box=box.ROUNDED)
        table.add_column("Setting", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        table.add_column("Status", style="yellow")

        table.add_row("GitHub Username", config.github_username, "✅ Configured")
        table.add_row("Output Directory", str(config.output_dir), "✅ Ready")
        table.add_row("Calendar Integration", "Enabled" if config.enable_calendar else "Disabled",
                     "✅ Ready" if config.enable_calendar else "⚠️  Disabled")
        table.add_row("Claude Tracking", "Enabled" if config.enable_claude_tracking else "Disabled",
                     "✅ Ready" if config.enable_claude_tracking else "⚠️  Disabled")

        console.print(table)

        # Show system checks
        console.print("\n🔍 [bold]System Checks:[/bold]")

        checks = Tree("System Dependencies")

        # Check GitHub CLI
        gh_status = "✅ Available" if os.system("which gh > /dev/null 2>&1") == 0 else "❌ Not found"
        checks.add(f"GitHub CLI: {gh_status}")

        # Check Google Workspace CLI
        gws_status = "✅ Available" if os.system("which gws > /dev/null 2>&1") == 0 else "❌ Not found"
        checks.add(f"Google Workspace CLI: {gws_status}")

        console.print(checks)

    except Exception as e:
        console.print(f"❌ Could not load configuration: {e}", style="red")
        console.print("💡 Run: [bold]receipts setup[/bold]", style="yellow")


def render_command(file_path_str: str, output: Optional[str], format: str, interactive: bool, display: bool = False, force: bool = False):
    """Render an existing report to a different format"""

    file_path = Path(file_path_str)

    # Validate input file
    if not file_path.exists():
        console.print(f"❌ [red]File not found:[/red] {file_path}", style="red")
        raise click.Abort()

    if not file_path.is_file():
        console.print(f"❌ [red]Path is not a file:[/red] {file_path}", style="red")
        raise click.Abort()

    console.print(f"📄 Rendering report: [bold]{file_path}[/bold]")
    console.print(f"🎯 Target format: [bold]{format.upper()}[/bold]")
    if display:
        console.print("📺 Output mode: [bold cyan]Display in CLI[/bold cyan]")

    # Check if we can use cached output (for both file and display modes)
    output_path = None
    use_cached = False
    cache_info = ""
    # Determine output file path to check caching (for both modes)
    if output and not display:
        output_path = Path(output)
    else:
        # Auto-generate output filename with new extension
        input_stem = file_path.stem
        format_extensions = {'markdown': 'md', 'html': 'html', 'json': 'json'}
        new_extension = format_extensions[format]
        output_path = file_path.parent / f"{input_stem}.{new_extension}"

        # If output would overwrite input, add suffix
        if output_path == file_path:
            output_path = file_path.parent / f"{input_stem}-converted.{new_extension}"

    # Check if cached output exists and is newer than input
    if not force and output_path.exists():
        input_mtime = file_path.stat().st_mtime
        output_mtime = output_path.stat().st_mtime

        if output_mtime > input_mtime:
            use_cached = True
            cache_info = f"⚡ [yellow]Cache available[/yellow] (use --force for fresh)"

            # For file mode, use cached file and return
            if not display:
                console.print(f"⚡ [yellow]Using cached output:[/yellow] {output_path}")
                console.print(f"💡 [dim]Use --force to regenerate[/dim]")

                # Show success message for cached result
                console.print()
                success_panel = Panel.fit(
                    f"✅ [bold green]Using cached report![/bold green]\n\n"
                    f"📁 Input: [bold]{file_path}[/bold]\n"
                    f"📄 Output: [bold]{output_path}[/bold]\n"
                    f"🎨 Format: [bold]{format.upper()}[/bold]\n"
                    f"⚡ [yellow]Cached (use --force to regenerate)[/yellow]",
                    title="🚀 Cache Hit",
                    border_style="yellow"
                )
                console.print(success_panel)

                # Offer to open file if interactive
                if interactive:
                    if click.confirm("🔍 Open the cached report?"):
                        os.system(f"code '{output_path}'" if os.system("which code > /dev/null 2>&1") == 0 else f"cat '{output_path}'")

                return
            else:
                # For display mode, show cache status but continue to display
                console.print(cache_info)
        else:
            cache_info = "🔄 [dim]Cache outdated, regenerating[/dim]"
            if display:
                console.print(cache_info)
    else:
        cache_info = "🆕 [dim]No cache found, generating fresh[/dim]"
        if display:
            console.print(cache_info)

    # Show progress with spinner
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:

        # For display mode with cache, read from cached file if available
        if display and use_cached and output_path.exists():
            task1 = progress.add_task("⚡ Reading cached output...", total=None)
            try:
                rendered_content = output_path.read_text(encoding='utf-8')
                progress.update(task1, description="✅ Cached output loaded")

                # Get the report metadata for display
                source_report = read_report(file_path)
            except Exception as e:
                progress.update(task1, description="❌ Failed to read cached file")
                console.print(f"❌ [red]Could not read cached file:[/red] {e}")
                use_cached = False  # Fall back to regeneration

        if not (display and use_cached):
            # Read the existing report and generate fresh content
            task1 = progress.add_task("📖 Reading report file...", total=None)
            try:
                report = read_report(file_path)
                source_report = report
                progress.update(task1, description="✅ Report file loaded")
            except Exception as e:
                progress.update(task1, description="❌ Failed to read report file")
                console.print(f"❌ [red]Could not read report:[/red] {e}")
                raise click.Abort()

            # Get the appropriate formatter
            task2 = progress.add_task("🎨 Preparing formatter...", total=None)
            try:
                if format == 'markdown':
                    formatter = MarkdownFormatter()
                elif format == 'html':
                    formatter = HTMLFormatter()
                elif format == 'json':
                    formatter = JSONFormatter()
                else:
                    raise ValueError(f"Unknown format: {format}")

                progress.update(task2, description="✅ Formatter ready")
            except Exception as e:
                progress.update(task2, description="❌ Formatter setup failed")
                console.print(f"❌ [red]Formatter error:[/red] {e}")
                raise click.Abort()

            # Generate the new report
            task3 = progress.add_task(f"🔄 Converting to {format.upper()}...", total=None)
            try:
                rendered_content = formatter.format(report)
                progress.update(task3, description=f"✅ Converted to {format.upper()}")
            except Exception as e:
                progress.update(task3, description="❌ Conversion failed")
                console.print(f"❌ [red]Conversion error:[/red] {e}")
                raise click.Abort()

    if display:
        # Display mode - show content in CLI
        console.print()

        # Prepare cache status for display
        cache_status = ""
        if use_cached:
            cache_status = f"⚡ [yellow]Cached output[/yellow]"
        else:
            cache_status = f"🔄 [green]Fresh render[/green]"

        if format == 'markdown':
            # Render markdown beautifully in CLI
            display_panel = Panel.fit(
                f"📄 [bold cyan]Rendered Report:[/bold cyan] {file_path.name}\n"
                f"🗓️  Date range: [bold]{source_report.date_range.start} to {source_report.date_range.end}[/bold]\n"
                f"📦 Status: {cache_status}",
                title="📖 Markdown Report",
                border_style="cyan"
            )
            console.print(display_panel)
            console.print()
            console.print(Markdown(rendered_content))

        elif format == 'json':
            # Show JSON with syntax highlighting
            display_panel = Panel.fit(
                f"📄 [bold cyan]Rendered Report:[/bold cyan] {file_path.name}\n"
                f"🗓️  Date range: [bold]{source_report.date_range.start} to {source_report.date_range.end}[/bold]\n"
                f"📦 Status: {cache_status}",
                title="📊 JSON Report",
                border_style="cyan"
            )
            console.print(display_panel)
            console.print()

            # Use Rich's JSON syntax highlighting
            from rich.syntax import Syntax
            syntax = Syntax(rendered_content, "json", theme="monokai", line_numbers=True)
            console.print(syntax)

        elif format == 'html':
            # For HTML, show a sample and suggest saving to file
            display_panel = Panel.fit(
                f"📄 [bold cyan]Rendered Report:[/bold cyan] {file_path.name}\n"
                f"🗓️  Date range: [bold]{source_report.date_range.start} to {source_report.date_range.end}[/bold]\n"
                f"📦 Status: {cache_status}\n\n"
                f"💡 [yellow]HTML is best viewed in a browser.[/yellow]\n"
                f"Consider using [bold]--output filename.html[/bold] to save it.",
                title="🌐 HTML Report",
                border_style="cyan"
            )
            console.print(display_panel)
            console.print()

            # Show first part of HTML
            preview = rendered_content[:1000] + "\n..." if len(rendered_content) > 1000 else rendered_content
            from rich.syntax import Syntax
            syntax = Syntax(preview, "html", theme="monokai", line_numbers=True)
            console.print(syntax)

        console.print()
        console.print("✨ [green]Display complete![/green]")

    else:
        # File mode - save to file (existing logic)
        # output_path already calculated above for caching

        # Check if output file already exists (unless it's the same as input)
        if output_path.exists() and output_path != file_path and not force:
            if interactive:
                if not click.confirm(f"⚠️  Output file exists: {output_path}\nOverwrite?"):
                    console.print("❌ Operation cancelled", style="yellow")
                    raise click.Abort()
            else:
                console.print(f"⚠️  [yellow]Output file exists and will be overwritten:[/yellow] {output_path}")

        # Write the rendered report
        try:
            output_path.write_text(rendered_content, encoding='utf-8')
        except Exception as e:
            console.print(f"❌ [red]Could not write output file:[/red] {e}")
            raise click.Abort()

        # Show success message
        console.print()
        success_panel = Panel.fit(
            f"✅ [bold green]Report rendered successfully![/bold green]\n\n"
            f"📁 Input: [bold]{file_path}[/bold]\n"
            f"📄 Output: [bold]{output_path}[/bold]\n"
            f"🎨 Format: [bold]{format.upper()}[/bold]\n"
            f"📊 Date range: [bold]{report.date_range.start} to {report.date_range.end}[/bold]",
            title="🎉 Render Complete",
            border_style="green"
        )
        console.print(success_panel)

        # Show preview if interactive and format is markdown
        if interactive and format == 'markdown':
            console.print("\n📖 [bold]Preview:[/bold]")
            preview = rendered_content[:800] + "..." if len(rendered_content) > 800 else rendered_content
            console.print(Markdown(preview))

        # Offer to open file
        if interactive:
            if click.confirm("🔍 Open the rendered report?"):
                os.system(f"code '{output_path}'" if os.system("which code > /dev/null 2>&1") == 0 else f"cat '{output_path}'")


def schedule_command(sub_command: Optional[str]):
    """Handle the 'receipts schedule' command"""

    if not sub_command:
        # Show schedule usage
        console.print("📅 [bold]Schedule Management[/bold]")
        console.print()
        console.print("💡 [yellow]Usage:[/yellow]")
        console.print("  receipts schedule daily     # Setup daily reports at 9am for yesterday")
        console.print("  receipts schedule weekly    # Setup weekly reports at 9am Mondays for last week")
        console.print("  receipts schedule status    # Show current schedule status")
        console.print("  receipts schedule disable   # Disable all scheduled reports")
        console.print()
        console.print("🎯 [cyan]Examples:[/cyan]")
        console.print("  receipts schedule daily     # Interactive setup for daily reports")
        console.print("  receipts schedule weekly    # Interactive setup for weekly reports")
        console.print("  receipts schedule status    # Check what's currently scheduled")
        console.print("  receipts schedule disable   # Remove all automation")
        return

    try:
        config = load_config()
    except Exception as e:
        console.print(f"❌ Configuration error: {e}", style="red")
        console.print("💡 Run 'receipts setup' to configure your system", style="yellow")
        raise click.Abort()

    scheduler = ScheduleManager()

    if sub_command == 'daily':
        console.print("📅 Setting up daily report scheduling...")

        # Ask for time preference
        time_input = click.prompt(
            "What time should daily reports be generated? (HH:MM, 24-hour format)",
            default="09:00"
        )

        # Ask for popup preference
        use_popup = click.confirm(
            "Use GUI popup for report display and reflection input?",
            default=True
        )

        console.print(f"\n📋 Configuration:")
        console.print(f"   Schedule: Daily at {time_input}")
        console.print(f"   Report: Yesterday's activities")
        console.print(f"   Interface: {'GUI Popup' if use_popup else 'Terminal'}")

        if not click.confirm("\nProceed with this configuration?"):
            console.print("❌ Setup cancelled", style="yellow")
            return

        # Setup the schedule
        success = scheduler.setup_daily_schedule(time_input, popup=use_popup)

        if success:
            # Update config
            config.schedule.daily_enabled = True
            config.schedule.daily_time = time_input
            config.schedule.popup_enabled = use_popup
            config.save()

            console.print(f"✅ Daily reports scheduled for {time_input} every day", style="green")
            console.print(f"   Mode: {'GUI Popup' if use_popup else 'Terminal'}")
            console.print(f"   Report: Yesterday's activities")
            console.print("\n💡 The schedule will run automatically. You can disable it with: receipts schedule disable")
        else:
            console.print("❌ Failed to setup daily scheduling", style="red")

    elif sub_command == 'weekly':
        console.print("📅 Setting up weekly report scheduling...")

        # Ask for day preference
        day_input = click.prompt(
            "What day of the week should weekly reports be generated?",
            default="monday",
            type=click.Choice(['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'])
        )

        # Ask for time preference
        time_input = click.prompt(
            "What time should weekly reports be generated? (HH:MM, 24-hour format)",
            default="09:00"
        )

        # Ask for popup preference
        use_popup = click.confirm(
            "Use GUI popup for report display and reflection input?",
            default=True
        )

        console.print(f"\n📋 Configuration:")
        console.print(f"   Schedule: Weekly on {day_input.title()}s at {time_input}")
        console.print(f"   Report: Previous week's activities (Monday-Sunday)")
        console.print(f"   Interface: {'GUI Popup' if use_popup else 'Terminal'}")

        if not click.confirm("\nProceed with this configuration?"):
            console.print("❌ Setup cancelled", style="yellow")
            return

        # Setup the schedule
        success = scheduler.setup_weekly_schedule(time_input, day_input, popup=use_popup)

        if success:
            # Update config
            config.schedule.weekly_enabled = True
            config.schedule.weekly_time = time_input
            config.schedule.weekly_day = day_input.lower()
            config.schedule.popup_enabled = use_popup
            config.save()

            console.print(f"✅ Weekly reports scheduled for {time_input} every {day_input.title()}", style="green")
            console.print(f"   Mode: {'GUI Popup' if use_popup else 'Terminal'}")
            console.print(f"   Report: Previous week's activities")
            console.print("\n💡 The schedule will run automatically. You can disable it with: receipts schedule disable")
        else:
            console.print("❌ Failed to setup weekly scheduling", style="red")

    elif sub_command == 'status':
        console.print("📅 Schedule Status")
        scheduler.print_schedule_status()

        # Also show config status
        console.print("\n⚙️ Configuration:")
        console.print(f"   Daily enabled: {'✅ Yes' if config.schedule.daily_enabled else '❌ No'}")
        if config.schedule.daily_enabled:
            console.print(f"   Daily time: {config.schedule.daily_time}")

        console.print(f"   Weekly enabled: {'✅ Yes' if config.schedule.weekly_enabled else '❌ No'}")
        if config.schedule.weekly_enabled:
            console.print(f"   Weekly time: {config.schedule.weekly_time} on {config.schedule.weekly_day.title()}s")

        if config.schedule.daily_enabled or config.schedule.weekly_enabled:
            console.print(f"   Interface mode: {'GUI Popup' if config.schedule.popup_enabled else 'Terminal'}")

    elif sub_command == 'disable':
        if not config.schedule.daily_enabled and not config.schedule.weekly_enabled:
            console.print("ℹ️ No scheduled reports are currently enabled", style="yellow")
            return

        console.print("🚫 Current scheduled reports:")
        if config.schedule.daily_enabled:
            console.print(f"   • Daily at {config.schedule.daily_time}")
        if config.schedule.weekly_enabled:
            console.print(f"   • Weekly on {config.schedule.weekly_day.title()}s at {config.schedule.weekly_time}")

        if not click.confirm("\nAre you sure you want to disable all scheduled reports?"):
            console.print("❌ Cancelled", style="yellow")
            return

        console.print("🚫 Disabling all scheduled reports...")

        success = scheduler.remove_all_schedules()

        if success:
            # Update config
            config.schedule.daily_enabled = False
            config.schedule.weekly_enabled = False
            config.save()

            console.print("✅ All scheduled reports disabled", style="green")
            console.print("💡 You can re-enable them anytime with: receipts schedule daily/weekly")
        else:
            console.print("❌ Failed to disable some scheduled reports", style="red")

    else:
        console.print(f"❌ Unknown schedule command: {sub_command}", style="red")
        console.print("💡 Use: receipts schedule [daily|weekly|status|disable]", style="yellow")


# Update the CLI docstring with the dynamic version
cli.__doc__ = cli.__doc__.replace("v0.2.0", f"v{__version__}")


def main():
    """Entry point for the CLI"""
    cli()


if __name__ == "__main__":
    main()