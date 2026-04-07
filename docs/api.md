# API Reference 📖

Complete reference for the `receipts` command line interface.

## Command Structure

```bash
receipts [TIMEFRAME] [OPTIONS]
receipts [FILE_PATH] [OPTIONS]  # Render mode
```

## Main Commands

### Generate Reports

```bash
receipts [TIMEFRAME] [OPTIONS]
```

**Arguments:**
- `TIMEFRAME` - Time period to generate report for

**Options:**
- `--output, -o PATH` - Output file path
- `--format, -f FORMAT` - Output format (markdown, html, json)
- `--no-calendar` - Skip calendar integration
- `--no-claude` - Skip Claude activity tracking
- `--interactive, -i` - Interactive mode with preview
- `--display, -d` - Display rendered report in CLI
- `--force` - Force regeneration (bypass cache)

### Setup Commands

```bash
receipts setup     # Interactive configuration
receipts status    # Show current configuration
```

## Timeframes

### Predefined Periods

| Timeframe | Description | Example Output File |
|-----------|-------------|-------------------|
| `today` | Current day | `today-2024-04-07.md` |
| `yesterday` | Previous day | `yesterday-2024-04-06.md` |
| `this-week` | Monday to today | `this-week-2024-W14.md` |
| `last-week` | Previous Monday-Sunday | `review-2024-W13.md` |
| (default) | Same as `last-week` | `review-2024-W13.md` |

### Custom Dates

| Format | Description | Example |
|--------|-------------|---------|
| `MM-DD` | Specific date (current year) | `04-07` |
| `MM-DD-YY` | Specific date with year | `04-07-24` |

## Render Mode

Auto-detected when TIMEFRAME is a file path:

```bash
receipts report.json --format html
receipts weekly-summary.md --display
```

### Render Options

All standard options plus:
- `--display, -d` - Show in terminal instead of saving
- `--force` - Override cache

## Output Formats

### Markdown (`markdown`)

```bash
receipts --format markdown
```

**Features:**
- GitHub-flavored markdown
- Rich formatting with emojis
- Reflection template included
- Perfect for documentation

**Example:**
```markdown
# Weekly Review: 2024-04-01 to 2024-04-07

## 🌟 Weekly Highlights

### 🎯 **Key Achievements**
- **Implemented new feature** with 15 commits
...
```

### HTML (`html`)

```bash
receipts --format html
```

**Features:**
- Responsive design
- Professional styling
- Interactive statistics cards
- Great for presentations

**Example:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Weekly Review</title>
    <style>/* Beautiful CSS */</style>
</head>
<body>
    <div class="stats">...</div>
</body>
</html>
```

### JSON (`json`)

```bash
receipts --format json
```

**Features:**
- Complete data structure
- Perfect for automation
- API integration ready
- Full round-trip fidelity

**Example:**
```json
{
  "date_range": {
    "start": "2024-04-01",
    "end": "2024-04-07"
  },
  "stats": {
    "total_contributions": 42
  }
}
```

## Configuration

### File Location

- **Primary:** `~/.config/what-did-i-get-done-this-week/config.json`
- **Project:** `.receipts.json` (optional)

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `RECEIPTS_GITHUB_USERNAME` | GitHub username | `"octocat"` |
| `RECEIPTS_OUTPUT_DIR` | Output directory | `"/reports/"` |
| `RECEIPTS_ENABLE_CALENDAR` | Enable calendar | `"false"` |

## Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | Success | Command completed successfully |
| `1` | Error | General error (file not found, parse error, etc.) |
| `2` | User Abort | User cancelled interactive prompt |

## Data Models

### WeeklyReport

Core data structure for all reports:

```python
class WeeklyReport:
    date_range: DateRange
    generated_at: datetime
    stats: WeeklyStats
    highlights: WeeklyHighlights
    daily_summaries: List[DailySummary]
    documentation_contributions: List[DocumentationContribution]
    metadata: Dict[str, Any]
```

### Key Statistics

```python
class WeeklyStats:
    total_contributions: int
    total_prs_created: int
    total_issues_created: int
    total_prs_reviewed: int
    total_meetings: int
    total_meeting_hours: float
    total_documentation_work: int
    most_productive_day: Optional[date]
    weekend_contributions: int
```

## Integration

### GitHub CLI

Requires `gh` CLI for GitHub integration:

```bash
# Check authentication
gh auth status

# Required scopes
gh auth login --scopes repo,read:org,read:user
```

### Google Workspace CLI

Optional `gws` CLI for calendar integration:

```bash
# Install
pip install google-workspace-cli

# Authenticate
gws auth login
```

## Examples

### Basic Usage

```bash
# Generate last week's report
receipts

# Today's activity
receipts today

# Interactive mode
receipts --interactive

# Custom format
receipts this-week --format html
```

### Render Examples

```bash
# Display in terminal
receipts report.json --format markdown --display

# Convert and save
receipts weekly.md --format html --output presentation.html

# Force fresh conversion
receipts cached-report.json --format markdown --force
```

### Advanced Usage

```bash
# Custom output location
receipts last-week --output ~/Desktop/weekly-review.md

# Disable integrations
receipts today --no-calendar --no-claude

# Specific date range
receipts 03-25 --format json --output march-report.json
```

## Troubleshooting

### Common Commands

```bash
# Check configuration
receipts status

# Validate setup
receipts setup

# Debug mode (verbose output)
receipts --interactive  # Shows detailed progress

# Reset configuration
rm ~/.config/what-did-i-get-done-this-week/config.json
receipts setup
```

### Log Files

Application logs (if enabled):
- **Location:** `~/.config/what-did-i-get-done-this-week/logs/`
- **Format:** JSON structured logging

---

**Back to:** [Documentation Home](index.md)