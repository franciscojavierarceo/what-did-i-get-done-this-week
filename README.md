# What did I get done this week? 📊

> **A professional accountability tool that generates comprehensive weekly reviews of your GitHub activity, calendar events, and accomplishments.**

Perfect for engineers, managers, and professionals who want to track their weekly impact and maintain accountability.

## ✨ What You Get

### 🌟 **Weekly Highlights**
- GitHub contribution summary with repository breakdown
- Meeting attendance categorized by type
- Most productive day analysis
- Work-life balance insights

### 📅 **Daily Breakdown**
- Structured day-by-day activity summary
- GitHub PRs, issues, and reviews with specific titles
- Required meetings only (filters out personal/declined events)
- Professional accomplishment tracking

### 📈 **Professional Insights**
- Code review impact across repositories
- Meeting patterns and time allocation
- Productivity trends and patterns
- Achievement validation for status updates

## 🚀 Quick Start

### One-Line Installation
```bash
# Local installation
git clone <this-repo>
cd weekly-review-skill
./setup.sh
```

### Manual Installation
```bash
# Download the files
curl -O https://example.com/weekly-review.sh
chmod +x weekly-review.sh

# Run setup
./setup.sh
```

## 📋 Prerequisites

- **GitHub CLI** (`gh`) - for accessing your GitHub data
- **jq** - for JSON processing
- **Google Workspace CLI** (optional) - for calendar integration

The setup script will install these automatically on macOS via Homebrew.

## 💡 Usage

```bash
# Generate review for last week
what-did-i-get-done-this-week

# Generate review for specific week
what-did-i-get-done-this-week 2024-03-25 2024-03-31

# View help
what-did-i-get-done-this-week --help
```

## 📊 Sample Output

```markdown
# Weekly Review: 2024-03-25 to 2024-03-31

## 🌟 Weekly Highlights

### 🎯 Key Achievements
- **42 GitHub contributions** across the week
- **34 code reviews** completed, primarily in: llamastack/llama-stack (18), feast-dev/feast (3)
- **1 Pull Request created:**
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

## ⚙️ Configuration

### Environment Variables
```bash
export GITHUB_USERNAME="your-username"          # Override detected username
export WEEKLY_REVIEW_DIR="/custom/path"         # Change output directory
```

### Calendar Integration
```bash
# Install Google Workspace CLI
brew install googleworkspace/cli/gws

# Authenticate
gws auth login

# Enable Calendar API in Google Cloud Console
# https://console.developers.google.com/apis/api/calendar-json.googleapis.com
```

## 🔧 Customization

### Meeting Filters
Edit the calendar filtering logic in `weekly-review.sh` to customize which events are included:

```bash
# Current filters exclude:
# - Personal events (daycare, writing, etc.)
# - Declined meetings
# - Working location markers
# - Busy/placeholder events
```

### Report Format
Modify the `generate_report()` function to customize the output format, add sections, or change styling.

## 🤖 Automation

### Weekly Cron Job
```bash
# Add to crontab (runs every Monday at 9 AM)
crontab -e

# Add this line:
0 9 * * 1 /path/to/what-did-i-get-done-this-week >> ~/weekly-review/weekly.log 2>&1
```

### Team Integration Ideas
- Slack bot for sharing team summaries
- Email reports to managers
- Integration with OKR tracking
- Dashboard aggregation for team metrics

## 🔒 Privacy & Security

- **Local Processing**: All data processing happens on your machine
- **No External Sharing**: Reports are stored locally in markdown format
- **API Access Only**: Only accesses GitHub/Google APIs with your permissions
- **Open Source**: Transparent code you can audit and modify

## 🛠️ Troubleshooting

### GitHub Issues
```bash
# Check authentication
gh auth status

# Re-authenticate
gh auth login

# Test API access
gh api user
```

### Calendar Issues
```bash
# Check Google Workspace CLI
gws auth status

# Test calendar access
gws calendar events list

# Enable Calendar API
# Visit: https://console.developers.google.com/apis/api/calendar-json.googleapis.com
```

### Common Problems
- **No contributions**: Check GitHub username and authentication
- **Missing meetings**: Verify calendar API permissions
- **Command not found**: Check PATH or restart terminal

## 🤝 Sharing with Your Team

This skill is designed to be easily shared! Here's how to get your team using it:

### Quick Team Setup
1. Share this repository with your team
2. Each person runs `./setup.sh`
3. Everyone gets their own personalized weekly reviews
4. No data sharing - everyone's reports stay private

### Benefits for Teams
- **Consistent reporting format** across the team
- **Easy status updates** for standups and 1:1s
- **Productivity insights** for individuals
- **Meeting pattern analysis** for team optimization

## 📈 Use Cases

- **Weekly 1:1s with managers** - structured talking points
- **Personal accountability** - track your professional impact
- **Performance reviews** - historical data on contributions
- **Time management** - understand meeting vs. coding time
- **Team retrospectives** - aggregate patterns and insights

## 🔄 Updates

To update the skill to the latest version:
```bash
cd ~/.local/share/weekly-review-skill
git pull
./setup.sh
```

## 🎯 Future Enhancements

Potential additions (contributions welcome!):
- Integration with Jira, Linear, or other project management tools
- Slack/Teams bot integration
- Web dashboard for team analytics
- Integration with time tracking tools
- Custom meeting categorization rules
- Export formats (PDF, CSV, JSON)

## 📄 License

MIT License - feel free to modify, share, and improve!

---

**Perfect for professional accountability and productivity tracking.**

*Built for engineers and managers who want to understand and communicate their weekly impact.*