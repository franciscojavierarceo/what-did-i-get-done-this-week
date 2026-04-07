# What Did I Get Done This Week? 🧾

[![PyPI version](https://badge.fury.io/py/what-did-i-get-done-this-week.svg)](https://badge.fury.io/py/what-did-i-get-done-this-week)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

> **Got the receipts on your productivity!** A beautiful CLI tool that tracks your GitHub activity, meetings, and accomplishments.

Turn your scattered work into organized weekly reports. Perfect for engineers, managers, and anyone who needs to answer "what did I do this week?" with actual data.

## ✨ Features

🎨 **Beautiful CLI** - Rich formatting, progress bars, and interactive setup
📊 **GitHub Integration** - Track commits, PRs, reviews, and issues
📅 **Calendar Integration** - Meeting tracking (Google Workspace)
🎯 **Multiple Formats** - Generate Markdown, HTML, and JSON reports
🔄 **Render Engine** - Convert between formats with caching
📺 **Display Mode** - View reports directly in your terminal
🤖 **AI Tracking** - Estimate Claude/AI-assisted development work
⚡ **Fast & Modern** - Built with uv, Python packaging at its finest

## 🚀 Quick Start

### Prerequisites

Install [uv](https://github.com/astral-sh/uv) (recommended) or use pip:

```bash
# Install uv (if you haven't already)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installation

```bash
# Install with uv (recommended)
uv pip install what-did-i-get-done-this-week

# Or with pip
pip install what-did-i-get-done-this-week
```

### Setup

```bash
# Interactive setup
receipts setup
```

The setup wizard configures:
- GitHub authentication
- Calendar integration (optional)
- Output preferences
- AI tracking settings

### Generate Your First Report

```bash
# Last week's receipts (default)
receipts

# This week so far
receipts this-week

# Yesterday's work
receipts yesterday

# Custom format
receipts last-week --format html

# Interactive mode with preview
receipts --interactive
```

## 🔄 Render Existing Reports

Convert and display reports in different formats:

```bash
# Display in terminal with beautiful formatting
receipts report.json --format markdown --display

# Convert formats
receipts weekly-report.md --format html --output presentation.html

# Auto-detects input format
receipts yesterday-2024-04-07.json --format markdown

# Force regeneration (bypasses cache)
receipts report.md --format html --force
```

## 📖 Sample Output

```markdown
# Weekly Review: 2024-04-01 to 2024-04-07

## 🌟 Weekly Highlights

### 🎯 **Key Achievements**
- **Implemented new render command** for receipts CLI
- **Added display mode** for beautiful CLI rendering
- **Fixed critical bug** in report generation

### 📝 **Documentation & Content**
- **Updated README** with render command examples

### 📅 **Meeting Highlights** (6.5 hours)
- **Sprint planning** went smoothly
- **Architecture decision** for new feature approved

### 📊 **Activity Patterns**
- **Most productive day:** Tuesday with 8 contributions
- **Consistent daily contributions** throughout week
```

## 🎨 Beautiful CLI Experience

```
╭───────────────────────────────────────────╮
│ 🎯 What Did I Get Done This Week?         │
│ Got the receipts on your productivity! 🧾 │
╰───────────────────────────────────────────╯

📄 Rendering report: weekly-summary.json
🎯 Target format: MARKDOWN
📺 Output mode: Display in CLI

╭────────── 📖 Markdown Report ───────────╮
│ 📄 Rendered Report: weekly-summary.json │
│ 🗓️  Date range: 2024-04-01 to 2024-04-07 │
╰─────────────────────────────────────────╯
```

## 🛠️ Development

### Using uv (recommended)

```bash
# Clone repository
git clone https://github.com/franciscojavierarceo/what-did-i-get-done-this-week
cd what-did-i-get-done-this-week

# Install dependencies
uv sync

# Run in development
uv run receipts --help

# Install in development mode
uv pip install -e .
```

### Using traditional pip

```bash
# Clone and install
git clone https://github.com/franciscojavierarceo/what-did-i-get-done-this-week
cd what-did-i-get-done-this-week
pip install -e .
```

### Running Tests

```bash
# With uv
uv run pytest

# With pip
pytest
```

## 📚 Documentation

- [Installation Guide](docs/installation.md)
- [Configuration](docs/configuration.md)
- [Render Command](docs/render.md)
- [API Reference](docs/api.md)

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch:** `git checkout -b feature/amazing-feature`
3. **Install dependencies:** `uv sync`
4. **Make your changes**
5. **Run tests:** `uv run pytest`
6. **Commit changes:** `git commit -m 'Add amazing feature'`
7. **Push to branch:** `git push origin feature/amazing-feature`
8. **Open a Pull Request**

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- Powered by [uv](https://github.com/astral-sh/uv) for fast Python package management
- Uses [Pydantic](https://github.com/pydantic/pydantic) for robust data validation
- GitHub CLI integration via [gh](https://cli.github.com/)

---

**Got questions?** [Open an issue](https://github.com/franciscojavierarceo/what-did-i-get-done-this-week/issues) or check out the [documentation](docs/).

**Star this repo** ⭐ if it helps you track your productivity!