# What did I get done this week

**Category**: productivity
**Version**: 2.0.0
**Description**: Beautiful Python CLI tool for generating comprehensive weekly reviews of your GitHub activity, calendar events, and professional accomplishments with modern uv package management.

## Overview

This skill creates detailed weekly summaries with a gorgeous terminal interface that combines:
- GitHub contributions (PRs, issues, reviews, commits)
- Calendar events (filtered to show only required meetings)
- Activity patterns and productivity insights
- Structured daily breakdowns with highlights

Perfect for:
- Weekly accountability check-ins
- Manager status updates
- Personal productivity tracking
- Team progress sharing

## Features

### 🎨 Beautiful CLI Interface
- Rich terminal output with colors, progress bars, and emojis
- Interactive setup and preview modes
- Smart error handling with helpful suggestions
- Professional formatted tables and panels

### 🌟 Smart Reporting
- Intelligent timeframe parsing (today, yesterday, this-week, last-week, MM-DD, MM-DD-YY)
- Multiple output formats (Markdown, HTML, JSON)
- Auto-generated file naming with timestamps
- Custom output paths and organization

### 📊 Comprehensive Data
- GitHub activity with repository breakdown
- Meeting attendance summary by type
- Most productive day analysis
- Work-life balance insights
- Documentation contribution tracking

### ⚙️ Smart Filtering
- Automatically excludes personal calendar events
- Shows only accepted/tentative meetings
- Filters out declined invitations
- Removes placeholder/busy events

## Prerequisites

### Required Tools
```bash
# Python 3.8+ (required)
python --version

# GitHub CLI (required)
gh auth login

# uv (recommended for development)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Optional Tools
```bash
# Google Workspace CLI (for calendar integration)
brew install googleworkspace/cli/gws
gws auth login
```

### Authentication
- **GitHub CLI**: Must be authenticated with read access to your repositories
- **Calendar Integration**: Optional, requires Google Workspace CLI and Calendar API access

## Installation

### Method 1: PyPI (Simplest)
```bash
# Install from PyPI
pip install what-did-i-get-done-this-week

# Setup and run
receipts setup
receipts
```

### Method 2: uv (Recommended for developers)
```bash
# Clone repository
git clone https://github.com/franciscojavierarceo/what-did-i-get-done-this-week
cd what-did-i-get-done-this-week

# Install with uv
uv sync

# Setup and run
uv run receipts setup
uv run receipts
```

### Method 3: Development Installation
```bash
# Clone and install in development mode
git clone <repo-url>
cd what-did-i-get-done-this-week
pip install -e ".[dev]"
```

## Usage

### Basic Commands
```bash
# Default: last week's receipts
receipts

# Specific timeframes
receipts today                 # Today's activity
receipts yesterday             # Yesterday's activity
receipts this-week             # This week so far
receipts last-week             # Last complete week

# Date formats
receipts 03-25                 # March 25th (current/last year)
receipts 03-25-24              # March 25, 2024
```

### With uv (recommended)
```bash
# All commands work with uv run:
uv run receipts                # Default (last week)
uv run receipts today         # Today's receipts
uv run receipts --interactive # Interactive mode
```

### Advanced Options
```bash
# Output formats
receipts --format markdown     # Default
receipts --format html        # HTML output
receipts --format json        # JSON data

# Customization
receipts --output custom.md    # Custom output file
receipts --no-calendar        # Skip calendar integration
receipts --no-claude          # Skip Claude activity tracking
receipts --interactive        # Interactive mode with preview

# Setup and status
receipts setup                # Interactive configuration
receipts status              # Check current setup
```

## Configuration

### Automatic Detection
The tool automatically detects:
- GitHub username from `gh` authentication
- Available integrations (GitHub CLI, Google Workspace CLI)
- Python environment and dependencies

### Manual Configuration
```bash
# Interactive setup wizard
receipts setup

# Check current configuration
receipts status
```

### Configuration Options
- **GitHub Username**: Auto-detected or manually specified
- **Output Directory**: Default `~/weekly-review/reports/` or custom path
- **Calendar Integration**: Enable/disable meeting tracking
- **Claude Tracking**: Enable/disable AI activity estimation
- **Default Format**: Markdown, HTML, or JSON

## Sample Output

### CLI Experience
```
╭─────────────────────────────────────────────────────────────────╮
│  🎯 What Did I Get Done This Week?                              │
│     Got the receipts on your productivity! 🧾                  │
╰─────────────────────────────────────────────────────────────────╯

📅 Generating report for: 2024-03-25 to 2024-03-31
👤 GitHub user: franciscojavierarceo

🔍 Fetching GitHub contributions... ✅
📝 Fetching PRs and issues... ✅
📅 Fetching calendar events... ✅
📊 Generating report... ✅

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                        🎉 Success                              ┃
┃  ✅ Report generated successfully!                             ┃
┃  📁 File: reports/review-2024-W13.md                           ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### Report Content
```markdown
# Weekly Review: 2024-03-25 to 2024-03-31

## 🌟 Weekly Highlights

### 🎯 **Key Achievements**
- **42 GitHub contributions** across the week
- **34 code reviews** completed, primarily in: llamastack/llama-stack (18), feast-dev/feast (3)
- **1 Pull Request created:** fix(vector_io): honor default_search_mode config

### 📝 **Documentation & Content**
- **11 documentation PR(s) reviewed**
- **1 blog post** contribution

### 📅 **Meeting Highlights** (17.1 hours)
- **24 professional meetings** attended
- **13 leadership/sync meetings** including 1:1s and team syncs

### 📊 **Activity Patterns**
- **Most productive day:** Tuesday with 12 GitHub contributions
- **Weekend contributions:** 2
```

## Development

### uv Workflow (recommended)
```bash
# Setup development environment
git clone <repo>
cd what-did-i-get-done-this-week
uv sync

# Run in development
uv run receipts

# Add dependencies
uv add <package>

# Run tests
uv run pytest

# Build package
uv build
```

### Traditional Workflow
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff check src/

# Type checking
mypy src/
```

## Automation

### Cron Job Setup
```bash
# Add to crontab for weekly reports every Monday at 9 AM
0 9 * * 1 cd /path/to/project && uv run receipts > weekly-report.log 2>&1
```

### Integration Ideas
- Slack bot integration for team sharing
- Email summaries to your manager
- Integration with OKR tracking tools
- Export to productivity dashboards
- GitHub Actions workflows

## Troubleshooting

### Common Issues
```bash
# Check GitHub CLI authentication
gh auth status

# Check Google Workspace CLI (if using calendar)
gws auth status

# Recreate virtual environment
rm -rf .venv && uv sync

# Check configuration
receipts status
```

### Error Messages
The CLI provides helpful error messages with next steps:
- GitHub authentication issues → `gh auth login`
- Missing configuration → `receipts setup`
- Invalid timeframes → Clear format examples
- Calendar integration problems → Setup instructions

## Contributing

This tool can be customized and extended:
- Add integration with other tools (Jira, Linear, Notion)
- Customize meeting categorization and filtering
- Add team-specific metrics and reporting
- Integrate with other calendar providers (Outlook, Exchange)
- Create custom output templates and themes

## Privacy & Security

- **Local processing** - All data processing happens on your machine
- **Secure storage** - Configuration stored in `~/.config/` with proper permissions
- **API permissions** - Uses existing GitHub CLI and Google Workspace CLI authentication
- **No external services** - No data sent to third-party services
- **Open source** - Full code transparency for security auditing

## Technology Stack

Built with modern Python tools:
- **[Rich](https://github.com/Textualize/rich)** - Beautiful terminal output
- **[Click](https://github.com/pallets/click)** - Command line interface
- **[Pydantic](https://github.com/pydantic/pydantic)** - Data validation and settings
- **[uv](https://github.com/astral-sh/uv)** - Fast Python package management
- **[GitHub CLI](https://cli.github.com/)** - GitHub API integration
- **[Google Workspace CLI](https://github.com/googleworkspace/cli)** - Calendar integration

## License

MIT License - feel free to modify and share!

---

**Created for professional accountability and productivity tracking.**
*Perfect for engineers, managers, and anyone who wants to track their weekly impact with a beautiful, modern CLI experience.*