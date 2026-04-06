# What did I get done this week

**Category**: productivity
**Version**: 1.0.0
**Description**: Generate comprehensive weekly reviews of your GitHub activity, calendar events, and professional accomplishments for accountability and progress tracking.

## Overview

This skill creates detailed weekly summaries that combine:
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

### 🌟 Weekly Highlights
- Key GitHub achievements with repository breakdown
- Meeting attendance summary by type
- Most productive day analysis
- Work-life balance insights

### 📊 Detailed Breakdowns
- Day-by-day GitHub activity with specific PRs/issues
- Required meetings only (excludes personal/declined events)
- Professional accomplishment tracking
- Structured markdown output

### ⚙️ Smart Filtering
- Automatically excludes personal calendar events
- Shows only accepted/tentative meetings
- Filters out declined invitations
- Removes placeholder/busy events

## Prerequisites

### Required Tools
```bash
# GitHub CLI (required)
gh auth login

# Google Workspace CLI (optional, for calendar integration)
brew install googleworkspace/cli/gws
gws auth login
```

### GitHub Authentication
The skill requires GitHub CLI to be authenticated with read access to your repositories.

### Calendar Integration (Optional)
For calendar events, you need:
1. Google Workspace CLI installed
2. Authentication: `gws auth login`
3. Calendar API enabled in your Google Cloud project

## Usage

### Basic Usage
```bash
# Generate review for last week
what-did-i-get-done-this-week

# Generate review for specific week
what-did-i-get-done-this-week 2024-03-25 2024-03-31
```

### Quick Setup
```bash
# Run the setup script
./setup.sh

# This will:
# - Check dependencies
# - Set up shell aliases
# - Configure authentication
# - Generate your first report
```

## Configuration

### GitHub Username
The skill auto-detects your GitHub username from `gh` authentication. To override:
```bash
export GITHUB_USERNAME="your-username"
```

### Output Directory
Reports are saved to `~/weekly-review/reports/`. To change:
```bash
export WEEKLY_REVIEW_DIR="/path/to/your/reports"
```

### Calendar Filtering
You can customize which events to exclude by editing the filter patterns in the script.

## Sample Output

```markdown
# Weekly Review: 2024-03-25 to 2024-03-31

## 🌟 Weekly Highlights

### 🎯 Key Achievements
- **42 GitHub contributions** across the week
- **34 code reviews** completed, primarily in: llamastack/llama-stack (18), feast-dev/feast (3)
- **1 Pull Request(s) created:**
  - fix(vector_io): honor default_search_mode config and fix sqlite-vec BM25 score inversion

### 📅 Meeting Highlights
- **54 professional meetings** attended
- **13 leadership/sync meetings** including 1:1s and team syncs
- **4 office hours sessions** hosted across different time zones

### 📊 Activity Patterns
- **Most productive day:** Tuesday with 12 GitHub contributions
- **Healthy work-life balance:** No weekend coding activity

## 📊 Weekly Summary

- **Monday 03/25:**
   - 5 GitHub contributions
     1. Reviewed: llamastack/llama-stack#5387: docs: blog post for llamastack observability
     2. Reviewed: llamastack/llama-stack#5383: ci: remove Mergify queue config
   - 9 required meetings
     1. 09:15 - Team Leadership Sync
     2. 10:00 - Sprint Planning
     3. 14:30 - 1:1 with Manager
```

## Installation

### Method 1: Direct Download
```bash
# Clone or download the skill files
curl -O https://example.com/weekly-review-skill.tar.gz
tar -xzf weekly-review-skill.tar.gz
cd weekly-review-skill
./install.sh
```

### Method 2: Manual Setup
1. Copy the `weekly-review.sh` script to your preferred location
2. Make it executable: `chmod +x weekly-review.sh`
3. Add to your PATH or create an alias
4. Run setup: `./setup.sh`

## Automation

### Weekly Cron Job
Set up automatic weekly reports:
```bash
# Run the automation setup
./cron-setup.sh

# This adds a cron job that runs every Monday at 9 AM
# Reports are automatically generated and logged
```

### Integration Ideas
- Slack bot integration for team sharing
- Email summaries to your manager
- Integration with OKR tracking tools
- Export to productivity dashboards

## Troubleshooting

### GitHub Issues
```bash
# Check GitHub CLI authentication
gh auth status

# Re-authenticate if needed
gh auth login
```

### Calendar Issues
```bash
# Check Google Workspace CLI
gws auth status

# Enable Calendar API
gws calendar events list
```

### Common Problems
- **No contributions showing**: Check GitHub username and authentication
- **Calendar events missing**: Verify Google Calendar API is enabled
- **Meetings not filtered**: Review calendar event permissions

## Contributing

This skill can be customized for different workflows:
- Add integration with other tools (Jira, Linear, etc.)
- Customize meeting categorization
- Add team-specific metrics
- Integrate with other calendar providers

## Privacy & Security

- All processing happens locally on your machine
- No data is sent to external services except the APIs you configure
- GitHub and calendar data stays private
- Reports are stored locally in markdown format

## License

MIT License - feel free to modify and share!

---

**Created for professional accountability and productivity tracking.**
*Perfect for engineers, managers, and anyone who wants to track their weekly impact.*