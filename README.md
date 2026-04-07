# What Did I Get Done This Week? 🧾

[![PyPI version](https://badge.fury.io/py/what-did-i-get-done-this-week.svg)](https://badge.fury.io/py/what-did-i-get-done-this-week)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Got the receipts on your productivity! A CLI tool for tracking what you actually got done.**

For engineers, managers, and anyone who wants to answer "what did I do this week?" with actual data.

## ✨ Features

🎨 **Nice CLI** with colors, progress bars, and interactive setup
📊 **GitHub Integration** - Track commits, PRs, reviews, and issues
📅 **Calendar Integration** - Meeting tracking (Google Workspace)
📝 **Documentation Tracking** - Blog posts, docs, README contributions
🤖 **AI Activity Tracking** - Estimate Claude/AI-assisted development work
🎯 **Multiple Output Formats** - Markdown, HTML, and JSON
⚡ **Fast & Reliable** - Uses GitHub CLI and Google Workspace CLI
🔧 **Configurable** - Interactive setup with good defaults

## 🚀 Quick Start

### Installation

```bash
# Install from PyPI
pip install what-did-i-get-done-this-week

# Or install from source
git clone https://github.com/franciscojavierarceo/what-did-i-get-done-this-week
cd what-did-i-get-done-this-week/python-v2
pip install -e .
```

### Setup

```bash
# Interactive setup (recommended)
what-did-i-get-done-this-week setup
```

The setup wizard will guide you through:
- GitHub authentication
- Calendar integration (optional)
- Output preferences
- Feature configuration

### Generate Your First Report

```bash
# Generate report for last week
what-did-i-get-done-this-week generate

# Interactive mode with preview
what-did-i-get-done-this-week generate --interactive

# Custom date range
what-did-i-get-done-this-week generate --start-date 2024-03-25

# Different output format
what-did-i-get-done-this-week generate --format html
```

## 📖 Sample Output

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

## 🎨 Beautiful CLI Experience

```
╭─────────────────────────────────────────────────────────────────╮
│  🎯 What Did I Get Done This Week?                              │
│     Got the receipts on your productivity! 🧾                  │
╰─────────────────────────────────────────────────────────────────╯

📅 Generating report for: 2024-03-25 to 2024-03-31
👤 GitHub user: your-username

🔍 Fetching GitHub contributions... ✅
📝 Fetching PRs and issues... ✅
📅 Fetching calendar events... ✅
🤖 Analyzing Claude activity... ✅
📊 Generating report... ✅

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                        🎉 Success                              ┃
┃                                                                ┃
┃  ✅ Report generated successfully!                             ┃
┃                                                                ┃
┃  📁 File: /Users/you/weekly-review/reports/review-2024-W13.md  ┃
┃  📊 Format: MARKDOWN                                           ┃
┃  🗓️  Period: 2024-03-25 to 2024-03-31                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## 🔧 Configuration

The tool uses a smart configuration system with interactive setup:

```bash
# Check current configuration
what-did-i-get-done-this-week status

# Reconfigure
what-did-i-get-done-this-week setup
```

### Configuration Options

- **GitHub Username** - Auto-detected from GitHub CLI
- **Output Directory** - Where to save reports
- **Calendar Integration** - Enable/disable meeting tracking
- **Claude Tracking** - Enable/disable AI activity estimation
- **Output Formats** - Markdown, HTML, or JSON

## 📅 Calendar Integration

For meeting tracking, install Google Workspace CLI:

```bash
# macOS
brew install googleworkspace/cli/gws

# Authenticate
gws auth login

# Enable Calendar API in Google Cloud Console
# https://console.developers.google.com/apis/api/calendar-json.googleapis.com
```

## 🤝 Use Cases

- **Weekly 1:1s with managers** - Actually have something to talk about
- **Personal tracking** - See what you actually did
- **Performance reviews** - Historical contribution data
- **Team retrospectives** - Understand work patterns
- **Client reports** - Show what you worked on
- **Time management** - Meeting vs. coding balance

## 🎯 Commands

```bash
# Core commands
what-did-i-get-done-this-week generate          # Generate report
what-did-i-get-done-this-week setup            # Interactive setup
what-did-i-get-done-this-week status           # Check configuration

# Generate options
--start-date YYYY-MM-DD    # Custom week start date
--output PATH              # Custom output file
--format FORMAT            # markdown, html, json
--no-calendar              # Skip calendar integration
--no-claude                # Skip Claude tracking
--interactive              # Interactive mode with preview

# Examples
what-did-i-get-done-this-week generate --interactive
what-did-i-get-done-this-week generate --start-date 2024-03-25 --format html
what-did-i-get-done-this-week generate --no-calendar --output custom-report.md
```

## 🔒 Privacy & Security

- **Local processing** - All data stays on your machine
- **Secure configuration** - Config stored in `~/.config/what-did-i-get-done-this-week/`
- **API access only** - Uses GitHub CLI and Google Workspace CLI permissions
- **No data sharing** - Reports are generated and stored locally
- **Open source** - Audit the code yourself

## 🛠️ Development

```bash
# Setup development environment
git clone https://github.com/franciscojavierarceo/what-did-i-get-done-this-week
cd what-did-i-get-done-this-week/python-v2

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff check src/

# Type checking
mypy src/
```

## 📈 Roadmap

- **Slack/Teams integration** for sharing summaries
- **Web dashboard** for team analytics
- **Custom templates** and themes
- **More integrations** (Jira, Linear, etc.)
- **Team aggregation** features
- **Export formats** (PDF, CSV)

## 🤝 Contributing

We welcome contributions! Please see our [contributing guide](CONTRIBUTING.md) for details on:
- Setting up the development environment with uv
- Code style and testing guidelines
- Adding new features and integrations
- Bug reports and feature requests

## 📄 License

MIT License - feel free to modify and share!

## 🙏 Acknowledgments

Built with love using:
- [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- [Click](https://github.com/pallets/click) for CLI interface
- [Pydantic](https://github.com/pydantic/pydantic) for data validation
- [GitHub CLI](https://cli.github.com/) for GitHub integration
- [Google Workspace CLI](https://github.com/googleworkspace/cli) for calendar integration

---

**Got the receipts on your productivity! 🚀**

*For engineers, managers, and anyone who wants to track what they actually get done.*