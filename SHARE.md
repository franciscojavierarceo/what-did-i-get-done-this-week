# Share: "What did I get done this week?" ⚡

> **Ready-to-share weekly accountability system for you and your team!**

## 🎯 What This Does

Automatically generates professional weekly reviews that show:
- **GitHub activity**: PRs, issues, reviews, commits with specific titles
- **Meeting summary**: Required meetings only (filtered intelligently)
- **Weekly highlights**: Key achievements and productivity patterns
- **Daily breakdown**: Structured day-by-day professional activity

## 📦 How to Share with Others

### Option 1: Direct Package Share
```bash
# Zip the entire skill package
tar -czf what-did-i-get-done-this-week.tar.gz weekly-review-skill/

# Share the file - recipient runs:
tar -xzf what-did-i-get-done-this-week.tar.gz
cd weekly-review-skill
./setup.sh
```

### Option 2: Git Repository
```bash
# Create a git repo and push to GitHub/GitLab
cd weekly-review-skill
git init
git add .
git commit -m "Initial commit: What did I get done this week skill"
# Push to your preferred git hosting

# Others can then:
git clone <your-repo-url>
cd weekly-review-skill
./setup.sh
```

### Option 3: Simple Script Share
```bash
# Just share the main script file
# Recipients need to manually install dependencies (gh, jq)
cp weekly-review.sh ~/Desktop/
# Share weekly-review.sh + quick setup instructions
```

## ⚡ Quick Start for Recipients

1. **Download/clone the skill package**
2. **Run setup**: `./setup.sh`
3. **Generate report**: `what-did-i-get-done-this-week`

The setup script handles:
- ✅ Installing dependencies (GitHub CLI, jq)
- ✅ Setting up authentication
- ✅ Creating command aliases
- ✅ Configuring directories

## 🎁 What Recipients Get

### Command Options
```bash
what-did-i-get-done-this-week              # Last week
what-did-i-get-done-this-week 2024-03-25 2024-03-31  # Custom range
```

### Sample Output Preview
```markdown
# Weekly Review: 2024-03-25 to 2024-03-31

## 🌟 Weekly Highlights
- **42 GitHub contributions** across the week
- **54 professional meetings** attended
- **Most productive day:** Tuesday with 12 contributions

## 📊 Weekly Summary
- **Monday 03/25:**
   - 5 GitHub contributions
     1. Reviewed: repo/project#123: Fix authentication bug
   - 9 required meetings
     1. 09:15 - Team Leadership Sync
```

## 🔧 Customization Options

Recipients can easily customize:

### Meeting Filters
Edit which calendar events to include/exclude

### Report Sections
Add or remove sections from the weekly report

### Output Format
Change markdown styling, add company branding

### Integration
Connect with Slack, email, or other tools

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
5. **Set up automation** for consistent reports

### Common Use Cases
- Weekly manager updates
- Performance review preparation
- Personal productivity tracking
- Team workload balancing
- Client activity reports

## 🚀 Getting Started

1. **Share this package** with your team/colleagues
2. **Everyone runs** `./setup.sh`
3. **Generate first report** to see the magic
4. **Customize** filters and format as needed
5. **Automate** with cron jobs if desired

---

**Ready to transform how you and your team track professional impact? Share away! 🎉**

*Each person gets their own private, powerful weekly accountability system.*