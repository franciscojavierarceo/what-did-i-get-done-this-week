# Configuration Guide ⚙️

Configure `receipts` to match your workflow and preferences.

## Interactive Setup

The easiest way to configure:

```bash
receipts setup
```

This wizard will guide you through all configuration options.

## Configuration File

Config is stored at `~/.config/what-did-i-get-done-this-week/config.json`

### Example Configuration

```json
{
  "github_username": "your-username",
  "output_dir": "~/weekly-review/reports/",
  "enable_calendar": true,
  "enable_claude_tracking": true,
  "default_format": "markdown"
}
```

## Configuration Options

### GitHub Settings

| Option | Description | Required | Example |
|--------|-------------|----------|---------|
| `github_username` | Your GitHub username | ✅ | `"octocat"` |

### Output Settings

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `output_dir` | Directory for reports | `~/weekly-review/reports/` | `"/path/to/reports/"` |
| `default_format` | Default output format | `"markdown"` | `"html"`, `"json"` |

### Integration Settings

| Option | Description | Default | Notes |
|--------|-------------|---------|-------|
| `enable_calendar` | Google Calendar integration | `true` | Requires `gws` CLI |
| `enable_claude_tracking` | AI activity estimation | `true` | Estimates AI usage |

## File Naming Conventions

Reports are automatically named based on timeframe:

| Timeframe | Filename Pattern | Example |
|-----------|------------------|---------|
| Today | `today-YYYY-MM-DD.{ext}` | `today-2024-04-07.md` |
| Yesterday | `yesterday-YYYY-MM-DD.{ext}` | `yesterday-2024-04-06.md` |
| This week | `this-week-YYYY-WNN.{ext}` | `this-week-2024-W14.md` |
| Last week | `review-YYYY-WNN.{ext}` | `review-2024-W13.md` |
| Custom date | `daily-YYYY-MM-DD.{ext}` | `daily-2024-03-25.md` |

## Command Line Overrides

Override config with command flags:

```bash
# Override output directory
receipts --output /tmp/my-report.md

# Override format
receipts --format html

# Disable calendar
receipts --no-calendar

# Disable AI tracking
receipts --no-claude
```

## Environment Variables

Set environment variables to override config:

```bash
export RECEIPTS_GITHUB_USERNAME="my-username"
export RECEIPTS_OUTPUT_DIR="/custom/path/"
export RECEIPTS_ENABLE_CALENDAR="false"
```

## Multiple Configurations

### Per-Project Config

Create `.receipts.json` in project directory:

```json
{
  "github_username": "work-account",
  "output_dir": "./reports/",
  "enable_calendar": false
}
```

### Profile-Based Config

Use different profiles:

```bash
# Personal reports
receipts --config ~/.config/receipts-personal.json

# Work reports
receipts --config ~/.config/receipts-work.json
```

## Advanced Settings

### Calendar Configuration

When enabling calendar integration, you can configure:

```json
{
  "calendar_config": {
    "exclude_patterns": [".*standup.*", ".*daily.*"],
    "include_weekends": false,
    "max_events_per_day": 20
  }
}
```

### Output Customization

```json
{
  "output_config": {
    "include_weekend_activity": true,
    "group_by_repository": true,
    "show_draft_prs": false
  }
}
```

## Checking Configuration

```bash
# View current configuration
receipts status

# Validate configuration
receipts setup --validate-only

# Reset to defaults
receipts setup --reset
```

## Troubleshooting

### Configuration Not Found

```bash
# Check config location
ls ~/.config/what-did-i-get-done-this-week/

# Run setup again
receipts setup
```

### Permission Issues

```bash
# Check directory permissions
ls -la ~/.config/what-did-i-get-done-this-week/

# Create directory if needed
mkdir -p ~/.config/what-did-i-get-done-this-week/
```

### GitHub Authentication

```bash
# Check GitHub CLI status
gh auth status

# Re-authenticate
gh auth login
```

---

**Next:** [Render Command →](render.md)