# Render Command 🔄

Convert and display reports between different formats with intelligent caching.

## Overview

The render command takes existing report files and converts them to different formats or displays them beautifully in your terminal.

## Basic Usage

```bash
# Auto-detect format and convert
receipts report.json --format markdown

# Display in terminal
receipts report.md --format markdown --display

# Custom output path
receipts weekly-summary.json --format html --output presentation.html
```

## Input Formats

### Supported Formats

| Format | Extension | Read Support | Notes |
|--------|-----------|--------------|-------|
| JSON | `.json` | ✅ Perfect | Full round-trip fidelity |
| Markdown | `.md`, `.markdown` | ✅ Basic | Extracts key metadata |
| HTML | `.html`, `.htm` | ❌ Planned | Use JSON/Markdown instead |

### Auto-Detection

The command automatically detects input format:

```bash
# These all work automatically
receipts report.json --format html
receipts weekly-summary.md --format json
receipts presentation.html --format markdown  # Error: not supported yet
```

## Output Modes

### File Mode (Default)

Save converted report to a file:

```bash
# Auto-generated filename
receipts report.json --format html
# Creates: report.html

# Custom filename
receipts report.json --format html --output presentation.html
```

### Display Mode

Show formatted content in terminal:

```bash
# Beautiful markdown rendering
receipts report.json --format markdown --display

# Syntax-highlighted JSON
receipts report.md --format json --display

# HTML preview
receipts report.json --format html --display
```

## Smart Caching

### How It Works

- Automatically caches converted files
- Checks if input file is newer than cached output
- Uses cached version when possible
- Significant performance improvement

### Cache Behavior

```bash
# First run - generates new file
receipts report.json --format html
# ✅ Report rendered successfully!

# Second run - uses cache
receipts report.json --format html
# ⚡ Using cached output: report.html

# After modifying input file - regenerates
touch report.json
receipts report.json --format html
# ✅ Report rendered successfully! (fresh)
```

### Cache Override

```bash
# Force regeneration
receipts report.json --format html --force
```

## Display Mode Examples

### Markdown Display

```bash
receipts weekly-report.json --format markdown --display
```

Output:
```
╭────────── 📖 Markdown Report ───────────╮
│ 📄 Rendered Report: weekly-report.json  │
│ 🗓️  Date range: 2024-04-01 to 2024-04-07 │
╰─────────────────────────────────────────╯

# Weekly Review: 2024-04-01 to 2024-04-07

## 🌟 Weekly Highlights
...
```

### JSON Display

```bash
receipts report.md --format json --display
```

Output with syntax highlighting:
```
╭──────────── 📊 JSON Report ─────────────╮
│ 📄 Rendered Report: report.md           │
│ 🗓️  Date range: 2024-04-01 to 2024-04-07 │
╰─────────────────────────────────────────╯

   1 {
   2   "date_range": {
   3     "start": "2024-04-01",
   4     "end": "2024-04-07"
   5   },
   6   "generated_at": "2024-04-07T10:00:00",
   7   ...
```

### HTML Display

```bash
receipts report.json --format html --display
```

Shows HTML preview with helpful message:
```
╭───────────────── 🌐 HTML Report ──────────────────╮
│ 📄 Rendered Report: report.json                   │
│ 🗓️  Date range: 2024-04-01 to 2024-04-07           │
│                                                   │
│ 💡 HTML is best viewed in a browser.              │
│ Consider using --output filename.html to save it. │
╰───────────────────────────────────────────────────╯

   1 <!DOCTYPE html>
   2 <html lang="en">
   3 <head>
   ...
```

## Advanced Usage

### Batch Conversion

```bash
# Convert multiple files
for file in reports/*.json; do
    receipts "$file" --format html
done

# Using find
find reports/ -name "*.json" -exec receipts {} --format markdown \;
```

### Integration with Other Tools

```bash
# Pipe to other commands
receipts report.json --format markdown --display | grep "achievements"

# Save and open in browser
receipts report.json --format html --output /tmp/report.html
open /tmp/report.html
```

### Interactive Mode

```bash
# Interactive with preview
receipts report.json --format html --interactive
```

Prompts for:
- File overwrite confirmation
- Preview display
- Option to open result file

## File Naming

### Auto-Generated Names

| Input | Format | Output |
|-------|--------|--------|
| `report.json` | `markdown` | `report.md` |
| `weekly-summary.md` | `html` | `weekly-summary.html` |
| `data.json` | `json` | `data-converted.json` |

### Collision Handling

If output would overwrite input:
- Adds `-converted` suffix
- `report.json` → `report-converted.json`

## Error Handling

### Common Errors

**File not found:**
```bash
receipts missing.json --format html
# ❌ File not found: missing.json
```

**Unsupported format:**
```bash
receipts report.html --format json
# ❌ HTML report reading is not yet implemented
```

**Parse errors:**
```bash
receipts invalid.json --format markdown
# ❌ Could not parse JSON report: Invalid JSON
```

### Recovery

```bash
# Validate JSON first
cat report.json | jq .

# Check file exists
ls -la report.json

# Use force flag to bypass cache issues
receipts report.json --format html --force
```

## Performance Tips

1. **Use caching** - Don't use `--force` unless needed
2. **Display mode** - Faster than file I/O for quick viewing
3. **JSON input** - Fastest parsing, full data fidelity
4. **Batch operations** - Process multiple files efficiently

## Roadmap

### Planned Features

- **HTML input support** with BeautifulSoup parsing
- **PDF output format** for presentations
- **Template customization** for HTML output
- **Diff mode** to compare reports
- **Streaming mode** for large files

---

**Next:** [API Reference →](api.md)