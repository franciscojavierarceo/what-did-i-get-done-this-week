# Installation Guide 🚀

Get up and running with `what-did-i-get-done-this-week` in minutes.

## Prerequisites

### Required

- **Python 3.8+**
- **GitHub CLI** (`gh`) - for GitHub integration
- **Git** - for repository access

### Recommended

- **[uv](https://github.com/astral-sh/uv)** - Fast Python package manager
- **Google Workspace CLI** (`gws`) - for calendar integration (optional)

## Install uv (Recommended)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

## Install the Package

### Option 1: uv (Recommended)

```bash
# Install from PyPI
uv pip install what-did-i-get-done-this-week

# Verify installation
receipts --version
```

### Option 2: pip

```bash
# Install from PyPI
pip install what-did-i-get-done-this-week

# Verify installation
receipts --version
```

### Option 3: Development Installation

```bash
# Clone repository
git clone https://github.com/franciscojavierarceo/what-did-i-get-done-this-week
cd what-did-i-get-done-this-week

# With uv (recommended)
uv sync
uv run receipts --version

# With pip
pip install -e .
receipts --version
```

## Setup Dependencies

### GitHub CLI

```bash
# macOS
brew install gh

# Ubuntu/Debian
sudo apt install gh

# Windows
winget install GitHub.cli

# Authenticate
gh auth login
```

### Google Workspace CLI (Optional)

For calendar integration:

```bash
# Install gws
pip install google-workspace-cli

# Or follow setup at: https://github.com/franciscojavierarceo/gws
```

## Initial Configuration

Run the interactive setup:

```bash
receipts setup
```

This will configure:
- GitHub authentication
- Output directory
- Calendar integration (optional)
- AI tracking preferences

## Verification

Test your installation:

```bash
# Check configuration
receipts status

# Generate a test report
receipts yesterday --interactive
```

## Troubleshooting

### Common Issues

**Command not found: `receipts`**
```bash
# Check installation
pip list | grep what-did-i-get-done-this-week

# Reinstall if needed
pip uninstall what-did-i-get-done-this-week
pip install what-did-i-get-done-this-week
```

**GitHub authentication issues**
```bash
# Check GitHub CLI
gh auth status

# Re-authenticate if needed
gh auth login
```

**Permission errors**
```bash
# Use user installation
pip install --user what-did-i-get-done-this-week

# Or use virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install what-did-i-get-done-this-week
```

### Getting Help

- [GitHub Issues](https://github.com/franciscojavierarceo/what-did-i-get-done-this-week/issues)
- [Configuration Guide](configuration.md)
- Check `receipts --help` for command options

---

**Next:** [Configuration Guide →](configuration.md)