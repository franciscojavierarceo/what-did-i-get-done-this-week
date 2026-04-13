"""
Configuration management for the weekly review system
"""

import os
import subprocess
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, validator
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
import click

console = Console()


class ScheduleConfig(BaseModel):
    """Configuration for automated scheduling"""
    daily_enabled: bool = False
    weekly_enabled: bool = False
    daily_time: str = "09:00"  # 24-hour format HH:MM
    weekly_time: str = "09:00"
    weekly_day: str = "monday"  # monday, tuesday, etc.
    popup_enabled: bool = True
    notification_timeout: int = 300  # 5 minutes for popup timeout
    fallback_to_terminal: bool = True

    @validator('weekly_day')
    def validate_weekday(cls, v):
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        if v.lower() not in valid_days:
            raise ValueError(f"Invalid weekday: {v}. Must be one of {valid_days}")
        return v.lower()

    @validator('daily_time', 'weekly_time')
    def validate_time(cls, v):
        import re
        if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', v):
            raise ValueError(f"Invalid time format: {v}. Must be HH:MM in 24-hour format")
        return v


class Config(BaseModel):
    """Configuration settings"""
    github_username: str
    output_dir: Path = Path.home() / "weekly-review" / "reports"
    template_dir: Path = Path.home() / "weekly-review" / "templates"
    enable_calendar: bool = True
    enable_claude_tracking: bool = True
    config_file: Path = Path.home() / ".config" / "what-did-i-get-done-this-week" / "config.json"
    schedule: ScheduleConfig = ScheduleConfig()

    class Config:
        json_encoders = {
            Path: lambda v: str(v),
        }

    @validator('output_dir', 'template_dir', 'config_file', pre=True)
    def ensure_path(cls, v):
        return Path(v) if isinstance(v, str) else v

    def save(self) -> None:
        """Save configuration to file"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            f.write(self.json(indent=2))

    @classmethod
    def load(cls, config_file: Optional[Path] = None) -> 'Config':
        """Load configuration from file"""
        if config_file is None:
            config_file = Path.home() / ".config" / "what-did-i-get-done-this-week" / "config.json"

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        with open(config_file, 'r') as f:
            data = f.read()

        config = cls.parse_raw(data)
        config.config_file = config_file
        return config


def detect_github_username() -> Optional[str]:
    """Try to detect GitHub username from GitHub CLI"""
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def check_github_cli() -> bool:
    """Check if GitHub CLI is available and authenticated"""
    try:
        subprocess.run(["gh", "auth", "status"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_google_workspace_cli() -> bool:
    """Check if Google Workspace CLI is available"""
    try:
        subprocess.run(["gws", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def setup_github_auth() -> bool:
    """Guide user through GitHub CLI authentication"""
    console.print("🔑 [bold]GitHub Authentication Required[/bold]")
    console.print("We need to authenticate with GitHub to fetch your activity data.\n")

    if not check_github_cli():
        console.print("❌ GitHub CLI not found. Please install it first:")
        console.print("   • macOS: [bold]brew install gh[/bold]")
        console.print("   • Other: https://cli.github.com/")
        return False

    if check_github_cli():
        console.print("✅ GitHub CLI is already authenticated!")
        return True

    console.print("Please run the following command to authenticate:")
    console.print("   [bold cyan]gh auth login[/bold cyan]")

    if Confirm.ask("Have you completed GitHub authentication?"):
        if check_github_cli():
            console.print("✅ GitHub authentication successful!")
            return True
        else:
            console.print("❌ Authentication failed. Please try again.")
            return False

    return False


def setup_calendar_integration() -> bool:
    """Guide user through calendar integration setup"""
    console.print("\n📅 [bold]Calendar Integration (Optional)[/bold]")
    console.print("Calendar integration tracks your meetings for comprehensive reports.\n")

    if not Confirm.ask("Do you want to enable calendar integration?", default=True):
        return False

    if not check_google_workspace_cli():
        console.print("⚠️  Google Workspace CLI not found.")
        console.print("To enable calendar integration:")
        console.print("   1. Install: [bold]brew install googleworkspace/cli/gws[/bold]")
        console.print("   2. Authenticate: [bold]gws auth login[/bold]")
        console.print("   3. Enable Calendar API in Google Cloud Console")

        enable_anyway = Confirm.ask("Skip calendar integration for now?", default=True)
        return not enable_anyway

    console.print("✅ Google Workspace CLI found!")

    # Test authentication
    try:
        subprocess.run(["gws", "auth", "status"], capture_output=True, check=True)
        console.print("✅ Google Workspace CLI is authenticated!")
        return True
    except subprocess.CalledProcessError:
        console.print("🔑 Please authenticate with Google Workspace CLI:")
        console.print("   [bold cyan]gws auth login[/bold cyan]")

        if Confirm.ask("Have you completed Google authentication?"):
            try:
                subprocess.run(["gws", "auth", "status"], capture_output=True, check=True)
                console.print("✅ Google authentication successful!")
                return True
            except subprocess.CalledProcessError:
                console.print("❌ Authentication failed. Calendar integration disabled.")
                return False

        return False


def setup_config() -> Config:
    """Interactive configuration setup"""

    # GitHub authentication
    if not setup_github_auth():
        raise click.ClickException("GitHub authentication is required")

    # Detect or ask for GitHub username
    detected_username = detect_github_username()
    if detected_username:
        console.print(f"🎯 Detected GitHub username: [bold cyan]{detected_username}[/bold cyan]")
        use_detected = Confirm.ask("Use this username?", default=True)
        github_username = detected_username if use_detected else Prompt.ask("Enter your GitHub username")
    else:
        github_username = Prompt.ask("Enter your GitHub username")

    # Calendar integration
    enable_calendar = setup_calendar_integration()

    # Claude tracking
    console.print("\n🤖 [bold]Claude Activity Tracking (Optional)[/bold]")
    console.print("Estimates your Claude AI usage for development work.\n")
    enable_claude = Confirm.ask("Enable Claude activity tracking?", default=True)

    # Output directory
    console.print("\n📁 [bold]Output Directory[/bold]")
    default_output = Path.home() / "weekly-review" / "reports"
    console.print(f"Default: [dim]{default_output}[/dim]")

    custom_path = Prompt.ask(
        "Custom output directory (or press Enter for default)",
        default="",
        show_default=False
    )

    output_dir = Path(custom_path) if custom_path else default_output

    # Create the config
    config = Config(
        github_username=github_username,
        output_dir=output_dir,
        enable_calendar=enable_calendar,
        enable_claude_tracking=enable_claude,
    )

    # Create directories
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.template_dir.mkdir(parents=True, exist_ok=True)

    # Save config
    config.save()

    # Show summary
    console.print("\n" + "="*60)
    console.print("📋 [bold]Configuration Summary[/bold]")
    console.print(f"   GitHub Username: [cyan]{config.github_username}[/cyan]")
    console.print(f"   Output Directory: [cyan]{config.output_dir}[/cyan]")
    console.print(f"   Calendar Integration: [cyan]{'Enabled' if config.enable_calendar else 'Disabled'}[/cyan]")
    console.print(f"   Claude Tracking: [cyan]{'Enabled' if config.enable_claude_tracking else 'Disabled'}[/cyan]")
    console.print("="*60)

    return config


def load_config() -> Config:
    """Load configuration with helpful error messages"""
    config_file = Path.home() / ".config" / "what-did-i-get-done-this-week" / "config.json"

    if not config_file.exists():
        raise click.ClickException(
            "Configuration not found. Please run: what-did-i-get-done-this-week setup"
        )

    try:
        return Config.load(config_file)
    except Exception as e:
        raise click.ClickException(f"Failed to load configuration: {e}")


def get_env_config() -> Optional[Config]:
    """Load configuration from environment variables (for backward compatibility)"""
    github_username = os.getenv("GITHUB_USERNAME")
    if not github_username:
        return None

    return Config(
        github_username=github_username,
        output_dir=Path(os.getenv("REVIEW_DIR", Path.home() / "weekly-review" / "reports")),
        template_dir=Path(os.getenv("TEMPLATE_DIR", Path.home() / "weekly-review" / "templates")),
        enable_calendar=os.getenv("ENABLE_CALENDAR", "true").lower() == "true",
        enable_claude_tracking=os.getenv("ENABLE_CLAUDE_TRACKING", "true").lower() == "true",
    )