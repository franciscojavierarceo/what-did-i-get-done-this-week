# Share: "What did I get done this week?" ⚡

> **Ready-to-share weekly accountability system for you and your team!**

## 🎯 What This Does

Automatically generates professional weekly reviews that show:
- **GitHub activity**: PRs, issues, reviews, commits with specific titles
- **Meeting summary**: Required meetings only (filtered intelligently)
- **Weekly highlights**: Key achievements and productivity patterns
- **Daily breakdown**: Structured day-by-day professional activity

## 📦 How to Share with Others

### Option 1: PyPI Installation (Easiest)
```bash
# Recipients just run:
pip install what-did-i-get-done-this-week
receipts setup
receipts
```

### Option 2: uv Installation (Recommended for developers)
```bash
# Clone and setup with uv
git clone https://github.com/franciscojavierarceo/what-did-i-get-done-this-week
cd what-did-i-get-done-this-week
uv sync
uv run receipts setup
uv run receipts
```

### Option 3: Direct Package Share
```bash
# Zip the entire project
tar -czf what-did-i-get-done-this-week.tar.gz what-did-i-get-done-this-week/

# Share the file - recipient runs:
tar -xzf what-did-i-get-done-this-week.tar.gz
cd what-did-i-get-done-this-week
uv sync
uv run receipts setup
```

## ⚡ Quick Start for Recipients

### Method 1: PyPI (Simplest)
```bash
pip install what-did-i-get-done-this-week
receipts setup
receipts
```

### Method 2: uv (Best for developers)
```bash
git clone <repo-url>
cd what-did-i-get-done-this-week
uv sync
uv run receipts
```

## 🎁 What Recipients Get

### Beautiful CLI Commands
```bash
receipts                    # Last week's receipts (default)
receipts today             # Today's receipts
receipts yesterday         # Yesterday's receipts
receipts this-week         # This week so far
receipts last-week         # Last week
receipts 03-25             # Specific date (MM-DD)
receipts 03-25-24          # Specific date (MM-DD-YY)
receipts setup             # Interactive setup
receipts status            # Check configuration
```

### Advanced Options
```bash
receipts --interactive           # Interactive mode with preview
receipts --format html          # HTML output
receipts --format json          # JSON output
receipts --no-calendar          # Skip calendar integration
receipts --output custom.md     # Custom output file
```

### Sample Output Preview
```markdown
# Weekly Review: 2024-03-25 to 2024-03-31

## 🌟 Weekly Highlights

### 🎯 **Key Achievements**
- **42 GitHub contributions** across the week
- **34 code reviews** completed, primarily in: llamastack/llama-stack (18)
- **1 Pull Request created:** fix(vector_io): honor default_search_mode config

### 📅 **Meeting Highlights** (17.1 hours)
- **24 professional meetings** attended
- **13 leadership/sync meetings** including 1:1s and team syncs

### 📊 **Activity Patterns**
- **Most productive day:** Tuesday with 12 GitHub contributions
- **Weekend contributions:** 2
```

## 🔧 Setup Requirements

Recipients need:

### Required
- **Python 3.8+**
- **GitHub CLI**: `brew install gh` (macOS) or equivalent
- **Git authentication**: `gh auth login`

### Optional (for calendar integration)
- **Google Workspace CLI**: `brew install googleworkspace/cli/gws`
- **Calendar auth**: `gws auth login`

## 🎨 Beautiful CLI Experience

Recipients get a gorgeous terminal interface with:
- 🎯 **Color-coded output** with emojis and styling
- ⚡ **Progress bars** for data fetching
- 📊 **Formatted tables** for configuration status
- 🎉 **Success panels** with clear file paths
- 💡 **Helpful error messages** with next steps

## 🔧 Customization Options

Recipients can easily customize:

### Meeting Filters
Edit which calendar events to include/exclude during setup

### Report Sections
Choose which data to include (GitHub, calendar, Claude tracking)

### Output Format
- Markdown (default) for readability
- HTML for sharing/presentations
- JSON for programmatic use

### File Naming
- Auto-generated timestamps
- Custom output paths
- Organized directory structure

## 🤝 Team Benefits

### For Individuals
- **Professional accountability** tracking
- **Easy status updates** for managers
- **Productivity pattern insights**
- **Historical achievement record**

### For Teams
- **Consistent reporting format**
- **Standardized productivity metrics**
- **Easy progress sharing**
- **Meeting pattern analysis**

### For Managers
- **Regular team updates** without micromanaging
- **Data-driven productivity insights**
- **Easy performance review prep**
- **Team workload visibility**

## 🎯 Perfect For

- **Engineering teams** tracking code contributions
- **Product managers** juggling meetings and deliverables
- **Consultants** needing client activity reports
- **Remote teams** wanting better visibility
- **Anyone** who wants weekly accountability

## 💡 Usage Tips to Share

### Best Practices
1. **Run every Monday morning** for last week's review
2. **Use for 1:1 prep** with managers
3. **Share highlights in team standups**
4. **Track patterns** over multiple weeks
5. **Set up automation** with cron jobs

### Common Use Cases
- Weekly manager updates: `receipts last-week`
- Daily standups: `receipts yesterday`
- Sprint reviews: `receipts this-week`
- Performance reviews: Historical reports
- Client updates: `receipts --format html`

### Power User Tips
```bash
# Interactive mode for first-time users
receipts --interactive

# Generate multiple formats for sharing
receipts --format html --output presentation.html
receipts --format json --output data.json

# Custom date ranges
receipts 03-25    # Specific day
receipts 03-25-24 # Different year
```

## 🚀 Getting Started

1. **Install** via PyPI or clone the repo
2. **Run setup** with `receipts setup`
3. **Generate first report** to see the magic
4. **Customize** filters and format as needed
5. **Share with team** using the methods above

### For Teams
```bash
# Share installation instructions
echo "pip install what-did-i-get-done-this-week && receipts setup"

# Or share the uv setup for developers
echo "git clone <repo> && cd <repo> && uv sync && uv run receipts setup"
```

## 🔒 Privacy & Security

- **Local processing** - All data stays on each person's machine
- **Secure config** - Settings stored in `~/.config/`
- **API permissions** - Uses existing GitHub/Google CLI auth
- **No central server** - Completely distributed
- **Open source** - Full code transparency

---

**Ready to transform how you and your team track professional impact? Share away! 🎉**

*Each person gets their own private, powerful weekly accountability system with a beautiful CLI interface.*