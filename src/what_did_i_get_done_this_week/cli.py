"""
Beautiful CLI interface for "What Did I Get Done This Week?"
"""

import click
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

console = Console()


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
@click.option('--output', '-o', type=click.Path(), help='Output file (auto-generated if not specified)')
@click.option('--format', '-f', type=click.Choice(['markdown', 'html', 'json']), default='markdown', help='Output format')
@click.option('--no-calendar', is_flag=True, help='Skip calendar integration')
@click.option('--no-claude', is_flag=True, help='Skip Claude activity tracking')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode with preview')
@click.option('--display', '-d', is_flag=True, help='Display rendered report in CLI instead of saving to file')
@click.option('--force', is_flag=True, help='Force regeneration even if cached output exists')
@click.version_option()
def cli(timeframe, output, format, no_calendar, no_claude, interactive, display, force):
    """🎯 What Did I Get Done This Week? v0.1.1

    Got the receipts on your productivity! A beautiful CLI tool for tracking
    your daily and weekly accomplishments.

    Usage:
      receipts                 # Last week's receipts (default)
      receipts this-week       # This week so far
      receipts last-week       # Last week
      receipts today          # Today's receipts
      receipts yesterday      # Yesterday's receipts
      receipts 03-25          # Specific date (MM-DD)
      receipts 03-25-24       # Specific date (MM-DD-YY)

    Render existing reports:
      receipts report.json --format html --display    # Show HTML in CLI
      receipts report.md --format markdown --display  # Show Markdown in CLI
      receipts report.json --format html --output presentation.html  # Save to file

    Setup:
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
        console.print("💡 Use: today, yesterday, this-week, last-week, MM-DD, or MM-DD-YY", style="yellow")
        raise click.Abort()

    # Determine if this is a daily or weekly report
    is_daily = date_range.start == date_range.end

    if is_daily:
        generate_daily_report(date_range, output, format, no_calendar, no_claude, interactive)
    else:
        generate_weekly_report(date_range, output, format, no_calendar, no_claude, interactive)


def generate_daily_report(date_range: DateRange, output, format, no_calendar, no_claude, interactive):
    """Generate a daily review report"""

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

    target_date = date_range.start
    date_name = "today" if target_date == date.today() else "yesterday" if target_date == date.today() - timedelta(days=1) else target_date.strftime("%Y-%m-%d")

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

    # Determine output file
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

    # Save report
    output.write_text(report, encoding='utf-8')

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

    # Show preview if interactive
    if interactive and format == 'markdown':
        console.print("\n📖 [bold]Preview:[/bold]")
        preview = report[:1000] + "..." if len(report) > 1000 else report
        console.print(Markdown(preview))

    # Offer to open file
    if interactive:
        if click.confirm("🔍 Open the report file?"):
            os.system(f"code '{output}'" if os.system("which code > /dev/null 2>&1") == 0 else f"cat '{output}'")


def generate_weekly_report(date_range: DateRange, output, format, no_calendar, no_claude, interactive):
    """Generate a weekly review report"""

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

    # Determine output file
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
            # This week (partial)
            output = reports_dir / f"this-week-{year}-W{week_num:02d}.{format}"
        else:
            # Complete week or last week
            output = reports_dir / f"review-{year}-W{week_num:02d}.{format}"
    else:
        output = Path(output)

    # Save report
    output.write_text(report, encoding='utf-8')

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

    # Show preview if interactive
    if interactive and format == 'markdown':
        console.print("\n📖 [bold]Preview:[/bold]")
        preview = report[:1000] + "..." if len(report) > 1000 else report
        console.print(Markdown(preview))

    # Offer to open file
    if interactive:
        if click.confirm("🔍 Open the report file?"):
            os.system(f"code '{output}'" if os.system("which code > /dev/null 2>&1") == 0 else f"cat '{output}'")


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

    # For file mode, check if we can use cached output
    output_path = None
    use_cached = False
    if not display:
        # Determine output file path first to check caching
        if output:
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

    if use_cached:
        return  # This shouldn't be reached, but just in case

    # Show progress with spinner
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:

        # Read the existing report
        task1 = progress.add_task("📖 Reading report file...", total=None)
        try:
            report = read_report(file_path)
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

        if format == 'markdown':
            # Render markdown beautifully in CLI
            display_panel = Panel.fit(
                f"📄 [bold cyan]Rendered Report:[/bold cyan] {file_path.name}\n"
                f"🗓️  Date range: [bold]{report.date_range.start} to {report.date_range.end}[/bold]",
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
                f"🗓️  Date range: [bold]{report.date_range.start} to {report.date_range.end}[/bold]",
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
                f"🗓️  Date range: [bold]{report.date_range.start} to {report.date_range.end}[/bold]\n\n"
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


def main():
    """Entry point for the CLI"""
    cli()


if __name__ == "__main__":
    main()