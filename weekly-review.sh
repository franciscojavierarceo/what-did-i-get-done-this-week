#!/bin/bash

# Weekly Review Generator
# Fetches GitHub activity and calendar events for the previous week

set -e

# Load environment variables from .env file if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
    echo "📋 Loading configuration from .env file..."
    source "$ENV_FILE"
elif [[ -f "$SCRIPT_DIR/.env.example" ]]; then
    echo "❌ No .env file found. Please copy .env.example to .env and configure your settings:"
    echo "   cp .env.example .env"
    echo "   # Then edit .env with your GitHub username and preferences"
    exit 1
else
    echo "⚠️  No .env file found, using default/environment settings"
fi

# Configuration with .env support
GITHUB_USERNAME="${GITHUB_USERNAME:-$(gh api user --jq '.login' 2>/dev/null)}"
REVIEW_DIR="${REVIEW_DIR:-$HOME/dev/weekly-review/reports}"
TEMPLATE_DIR="${TEMPLATE_DIR:-$HOME/dev/weekly-review/templates}"
ENABLE_CALENDAR="${ENABLE_CALENDAR:-true}"
ENABLE_CLAUDE_TRACKING="${ENABLE_CLAUDE_TRACKING:-true}"

# Validate required configuration
if [[ -z "$GITHUB_USERNAME" || "$GITHUB_USERNAME" == "your-username" ]]; then
    echo "❌ GitHub username not configured. Please:"
    echo "   1. Copy .env.example to .env: cp .env.example .env"
    echo "   2. Edit .env and set GITHUB_USERNAME=your-actual-username"
    echo "   3. Or ensure 'gh auth login' is completed"
    exit 1
fi

echo "👤 Using GitHub username: $GITHUB_USERNAME"

# Create directories if they don't exist
mkdir -p "$REVIEW_DIR"
mkdir -p "$TEMPLATE_DIR"

# Calculate date ranges (previous week: Monday to Sunday)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS date commands
    LAST_MONDAY=$(date -v-mon -v-7d +%Y-%m-%d)
    LAST_SUNDAY=$(date -v-sun -v-7d +%Y-%m-%d)
    WEEK_START="${LAST_MONDAY}T00:00:00Z"
    WEEK_END="${LAST_SUNDAY}T23:59:59Z"
    WEEK_LABEL=$(date -j -f "%Y-%m-%d" "$LAST_MONDAY" +"%Y-W%U")
else
    # Linux date commands
    LAST_MONDAY=$(date -d "last monday - 7 days" +%Y-%m-%d)
    LAST_SUNDAY=$(date -d "last sunday" +%Y-%m-%d)
    WEEK_START="${LAST_MONDAY}T00:00:00Z"
    WEEK_END="${LAST_SUNDAY}T23:59:59Z"
    WEEK_LABEL=$(date -d "$LAST_MONDAY" +"%Y-W%U")
fi

# Allow custom date range via arguments (Monday to Sunday)
if [ $# -eq 2 ]; then
    WEEK_START="${1}T00:00:00Z"
    WEEK_END="${2}T23:59:59Z"
    WEEK_LABEL=$(date -j -f "%Y-%m-%d" "$1" +"%Y-W%U" 2>/dev/null || date -d "$1" +"%Y-W%U")
    LAST_MONDAY=$1
    LAST_SUNDAY=$2

    # Ensure we're working with Monday-Sunday range
    echo "📅 Using custom range: Monday $LAST_MONDAY to Sunday $LAST_SUNDAY"
fi

echo "📅 Generating weekly review for $LAST_MONDAY to $LAST_SUNDAY"
echo "📁 Week label: $WEEK_LABEL"

# Output file
OUTPUT_FILE="$REVIEW_DIR/review-$WEEK_LABEL.md"

# Function to fetch GitHub contributions
fetch_github_contributions() {
    echo "🔍 Fetching GitHub contributions..." >&2

    local contrib_data
    contrib_data=$(gh api graphql -f query="
    {
      viewer {
        login
        contributionsCollection(from: \"$WEEK_START\", to: \"$WEEK_END\") {
          totalCommitContributions
          totalIssueContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }")

    echo "$contrib_data"
}

# Function to fetch created PRs
fetch_created_prs() {
    echo "🔍 Fetching created PRs..." >&2
    gh search prs --author="$GITHUB_USERNAME" --created="$LAST_MONDAY..$LAST_SUNDAY" --json title,url,repository,createdAt,state,number
}

# Function to fetch created issues
fetch_created_issues() {
    echo "🔍 Fetching created issues..." >&2
    gh search issues --author="$GITHUB_USERNAME" --created="$LAST_MONDAY..$LAST_SUNDAY" --json title,url,repository,createdAt,state,number
}

# Function to fetch documentation contributions
fetch_documentation_contributions() {
    echo "🔍 Fetching documentation contributions..." >&2

    # Get all PRs and filter for documentation-related ones
    local all_created_prs all_created_issues all_reviewed_prs

    # Filter existing data for documentation-related content
    all_created_prs=$(echo "$CREATED_PRS" | jq '[.[] | select(.title | test("docs?:|documentation|blog|readme|README|tutorial|guide"; "i"))]' 2>/dev/null || echo "[]")
    all_created_issues=$(echo "$CREATED_ISSUES" | jq '[.[] | select(.title | test("docs?:|documentation|blog|readme|README|tutorial|guide"; "i"))]' 2>/dev/null || echo "[]")

    # For reviewed PRs, we need to filter from the GraphQL result
    all_reviewed_prs=$(echo "$REVIEWED_PRS" | jq '[.data.search.nodes[] | select(.title | test("docs?:|documentation|blog|readme|README|tutorial|guide"; "i"))]' 2>/dev/null || echo "[]")

    # Combine all documentation work
    echo "{
        \"created_prs\": $all_created_prs,
        \"created_issues\": $all_created_issues,
        \"reviewed_prs\": $all_reviewed_prs
    }"
}

# Function to fetch reviewed PRs
fetch_reviewed_prs() {
    echo "🔍 Fetching reviewed PRs..." >&2
    gh api graphql -f query="
    {
      search(query: \"reviewed-by:$GITHUB_USERNAME created:$LAST_MONDAY..$LAST_SUNDAY\", type: ISSUE, first: 50) {
        issueCount
        nodes {
          ... on PullRequest {
            title
            url
            repository {
              nameWithOwner
            }
            createdAt
            state
            number
          }
        }
      }
    }"
}

# Function to fetch PRs in progress (your open PRs with activity this week)
fetch_prs_in_progress() {
    echo "🔍 Fetching PRs in progress..." >&2

    # Get your open PRs
    local open_prs
    open_prs=$(gh search prs --author="$GITHUB_USERNAME" --state=open --json title,url,repository,createdAt,number --limit 20)

    # For each open PR, check if there were commits this week
    echo "$open_prs" | jq -c '.[]' | while read -r pr; do
        local repo_name title number url created_at
        repo_name=$(echo "$pr" | jq -r '.repository.nameWithOwner')
        title=$(echo "$pr" | jq -r '.title')
        number=$(echo "$pr" | jq -r '.number')
        url=$(echo "$pr" | jq -r '.url')
        created_at=$(echo "$pr" | jq -r '.createdAt')

        # Check for commits by you on this PR during the week
        local commits_this_week
        commits_this_week=$(gh api graphql -f query="
        {
          search(query: \"repo:$repo_name author:$GITHUB_USERNAME committer-date:$LAST_MONDAY..$LAST_SUNDAY\", type: COMMIT, first: 50) {
            nodes {
              ... on Commit {
                oid
                message
                committedDate
                associatedPullRequests(first: 5) {
                  nodes {
                    number
                  }
                }
              }
            }
          }
        }" 2>/dev/null | jq -r --arg pr_num "$number" '
        .data.search.nodes[] |
        select(.associatedPullRequests.nodes[]?.number == ($pr_num | tonumber)) |
        {
          message: (.message | split("\n")[0]),
          date: .committedDate,
          oid: .oid[0:7]
        } |
        "\(.date)|\(.oid)|\(.message)"
        ' 2>/dev/null)

        if [[ -n "$commits_this_week" ]]; then
            echo "ACTIVE_PR|$repo_name|$number|$title|$url|$created_at"
            echo "$commits_this_week" | while read -r commit_info; do
                echo "COMMIT|$commit_info"
            done
        fi
    done
}

# Function to analyze actual Claude conversation activity
fetch_claude_conversation_activity() {
    echo "🔍 Analyzing Claude conversation activity..." >&2

    local claude_data='{"conversations": [], "sessions": 0, "exploratory_work": [], "pr_related_work": []}'

    # Method 1: Check for Claude Code CLI usage with better date filtering
    if [[ -f ~/.zsh_history ]]; then
        local daily_claude_usage
        daily_claude_usage=$(grep "claude\|anthropic" ~/.zsh_history 2>/dev/null | wc -l || echo "0")
        claude_data=$(echo "$claude_data" | jq --arg usage "$daily_claude_usage" '.total_cli_commands = ($usage | tonumber)')
    fi

    # Method 2: Check for Claude conversation files (if they exist)
    local conversation_dir="$HOME/.anthropic/conversations"
    if [[ -d "$conversation_dir" ]]; then
        local weekly_conversations
        weekly_conversations=$(find "$conversation_dir" -name "*.json" -newermt "$LAST_MONDAY" ! -newermt "$(date -d "$LAST_SUNDAY + 1 day" +%Y-%m-%d)" 2>/dev/null | wc -l || echo "0")
        claude_data=$(echo "$claude_data" | jq --arg convs "$weekly_conversations" '.conversations_found = ($convs | tonumber)')
    fi

    # Method 3: Estimate sessions from shell history patterns
    local estimated_sessions
    estimated_sessions=$(grep -E "claude|anthropic|ai" ~/.zsh_history 2>/dev/null | grep -v "grep\|history" | wc -l || echo "0")
    estimated_sessions=$((estimated_sessions / 3))  # Rough estimate: 3 commands per session

    claude_data=$(echo "$claude_data" | jq --arg sessions "$estimated_sessions" '.estimated_sessions = ($sessions | tonumber)')

    echo "$claude_data"
}

# Function to categorize Claude work
categorize_claude_work() {
    local claude_data="$1"
    local prs_in_progress="$2"

    # Extract potential work categories
    local total_sessions
    total_sessions=$(echo "$claude_data" | jq -r '.estimated_sessions // 0')

    if [[ "$total_sessions" -gt 0 ]]; then
        # Rough categorization based on your workflow patterns
        local pr_related_sessions=$((total_sessions * 60 / 100))  # 60% PR-related
        local exploratory_sessions=$((total_sessions * 40 / 100))  # 40% exploratory

        echo "PR_RELATED|$pr_related_sessions"
        echo "EXPLORATORY|$exploratory_sessions"
    fi
}

# Function to fetch calendar events (if gws is available)
fetch_calendar_events() {
    echo "📅 Fetching calendar events..." >&2

    if command -v gws >/dev/null 2>&1; then
        echo "Using Google Workspace CLI..." >&2
        gws calendar events list --params "{\"calendarId\": \"primary\", \"timeMin\": \"$WEEK_START\", \"timeMax\": \"$WEEK_END\", \"maxResults\": 100, \"singleEvents\": true, \"orderBy\": \"startTime\"}" --format json 2>/dev/null || {
            echo "⚠️  Calendar fetch failed - check API enablement and authentication" >&2
            return 1
        }
    else
        echo "⚠️  Google Workspace CLI (gws) not found. Install it for calendar integration." >&2
        echo "   See: https://github.com/googleworkspace/cli" >&2
        return 1
    fi
}

# Function to estimate Claude usage
fetch_claude_activity() {
    echo "🤖 Analyzing Claude activity..." >&2

    local claude_data='{"daily_usage": []}'

    # Method 1: Check shell history for Claude Code CLI usage
    if [[ -f ~/.zsh_history ]]; then
        local claude_cli_usage
        claude_cli_usage=$(grep -c "claude\|anthropic" ~/.zsh_history 2>/dev/null || echo "0")
        if [[ "$claude_cli_usage" -gt 0 ]]; then
            claude_data=$(echo "$claude_data" | jq --arg usage "$claude_cli_usage" '.cli_usage = ($usage | tonumber)')
        fi
    fi

    # Method 2: Check browser history for claude.ai (Safari/Chrome)
    local browser_visits=0

    # Safari history (requires sqlite3)
    if [[ -f ~/Library/Safari/History.db ]]; then
        local safari_claude
        safari_claude=$(sqlite3 ~/Library/Safari/History.db "SELECT COUNT(*) FROM history_items WHERE url LIKE '%claude.ai%' AND datetime(visit_time + 978307200, 'unixepoch') BETWEEN '$WEEK_START' AND '$WEEK_END';" 2>/dev/null || echo "0")
        browser_visits=$((browser_visits + safari_claude))
    fi

    # Chrome history (requires sqlite3)
    if [[ -f ~/Library/Application\ Support/Google/Chrome/Default/History ]]; then
        # Chrome locks the history file, so we'd need to copy it first
        local chrome_claude=0  # Simplified for now
        browser_visits=$((browser_visits + chrome_claude))
    fi

    claude_data=$(echo "$claude_data" | jq --arg visits "$browser_visits" '.browser_visits = ($visits | tonumber)')

    # Method 3: Estimate based on typical usage patterns (you can customize this)
    local estimated_sessions=0
    if [[ "$browser_visits" -gt 0 ]]; then
        estimated_sessions=$((browser_visits / 3))  # Rough estimate: 3 visits per session
    fi

    claude_data=$(echo "$claude_data" | jq --arg sessions "$estimated_sessions" '.estimated_sessions = ($sessions | tonumber)')

    echo "$claude_data"
}

# Function to parse Claude activity for a specific day
get_claude_activity_for_day() {
    local date="$1"
    local claude_data="$2"

    # For now, return estimated daily activity
    # This could be enhanced to parse actual conversation logs by date

    local cli_usage browser_visits
    cli_usage=$(echo "$claude_data" | jq -r '.cli_usage // 0')
    browser_visits=$(echo "$claude_data" | jq -r '.browser_visits // 0')

    # Simple daily distribution (you can make this smarter)
    local daily_cli=$((cli_usage / 7))  # Distribute across week
    local daily_browser=$((browser_visits / 7))

    if [[ "$daily_cli" -gt 0 ]] || [[ "$daily_browser" -gt 0 ]]; then
        local total_interactions=$((daily_cli + daily_browser))
        echo "   - ~$total_interactions Claude interactions (CLI: $daily_cli, Web: $daily_browser)"
    fi
}

# Function to parse contributions and generate daily breakdown
parse_daily_contributions() {
    local contrib_data="$1"
    echo "$contrib_data" | jq -r '
    .data.viewer.contributionsCollection.contributionCalendar.weeks[].contributionDays[] |
    "- **\(.date)**: \(.contributionCount) contributions"'
}

# Function to fetch activity timing patterns from GitHub
fetch_activity_timing_patterns() {
    local start_date="$1"
    local end_date="$2"

    # Get commits with timestamps for the week
    local commits_with_time
    commits_with_time=$(gh api graphql -f query="
    {
      search(query: \"author:$GITHUB_USERNAME committer-date:$start_date..$end_date\", type: COMMIT, first: 100) {
        nodes {
          ... on Commit {
            committedDate
            message
            repository {
              nameWithOwner
            }
          }
        }
      }
    }" 2>/dev/null | jq -r '.data.search.nodes[]? | .committedDate' 2>/dev/null)

    if [[ -z "$commits_with_time" ]]; then
        return
    fi

    # Analyze timing patterns
    local evening_count night_count morning_count
    evening_count=0
    night_count=0
    morning_count=0

    while IFS= read -r timestamp; do
        if [[ -n "$timestamp" ]]; then
            # Extract hour from timestamp (assuming format: 2026-03-30T22:15:30Z)
            local hour
            hour=$(echo "$timestamp" | grep -o 'T[0-9][0-9]:' | sed 's/T//' | sed 's/://')

            if [[ "$hour" =~ ^[0-9]+$ ]]; then
                if [[ "$hour" -ge 22 ]] || [[ "$hour" -le 2 ]]; then
                    ((night_count++))
                elif [[ "$hour" -ge 18 ]] && [[ "$hour" -lt 22 ]]; then
                    ((evening_count++))
                elif [[ "$hour" -ge 6 ]] && [[ "$hour" -lt 10 ]]; then
                    ((morning_count++))
                fi
            fi
        fi
    done <<< "$commits_with_time"

    # Generate timing insights
    local total_timed_commits=$((evening_count + night_count + morning_count))
    if [[ "$total_timed_commits" -gt 0 ]]; then
        if [[ "$night_count" -ge 2 ]]; then
            local night_percentage=$((night_count * 100 / total_timed_commits))
            echo "- **Late night coder:** $night_count commits between 10 PM - 2 AM ($night_percentage% of timed activity)"
        elif [[ "$evening_count" -ge 2 ]]; then
            local evening_percentage=$((evening_count * 100 / total_timed_commits))
            echo "- **Evening productivity:** $evening_count commits between 6-10 PM ($evening_percentage% of timed activity)"
        elif [[ "$morning_count" -ge 2 ]]; then
            local morning_percentage=$((morning_count * 100 / total_timed_commits))
            echo "- **Early bird:** $morning_count commits between 6-10 AM ($morning_percentage% of timed activity)"
        fi
    fi
}

# Function to generate weekly highlights
generate_weekly_highlights() {
    local contrib_data="$1"
    local created_prs="$2"
    local created_issues="$3"
    local reviewed_prs="$4"
    local calendar_events="$5"
    local documentation_contributions="$6"

    echo "## 🌟 Weekly Highlights"
    echo ""

    # Extract key metrics
    local total_contributions total_prs total_issues total_reviews
    total_contributions=$(echo "$contrib_data" | jq -r '.data.viewer.contributionsCollection.contributionCalendar.totalContributions')
    total_prs=$(echo "$created_prs" | jq 'length')
    total_issues=$(echo "$created_issues" | jq 'length')
    total_reviews=$(echo "$reviewed_prs" | jq -r '.data.search.issueCount // 0')

    # Key achievements section
    echo "### 🎯 **Key Achievements**"

    # GitHub highlights
    if [[ "$total_contributions" -gt 0 ]]; then
        echo "- **$total_contributions GitHub contributions** across the week"

        if [[ "$total_reviews" -gt 0 ]]; then
            # Get top repositories reviewed (filter by week range)
            local top_repos
            top_repos=$(echo "$reviewed_prs" | jq -r --arg week_start "$WEEK_START" --arg week_end "$WEEK_END" '
                .data.search.nodes[] |
                select(.createdAt >= $week_start and .createdAt < $week_end) |
                .repository.nameWithOwner
            ' | sort | uniq -c | sort -nr | head -3 | awk '{print $2 " (" $1 ")"}' | tr '\n' ', ' | sed 's/, $//')

            # Count actual reviews in date range
            local week_reviews
            week_reviews=$(echo "$reviewed_prs" | jq -r --arg week_start "$WEEK_START" --arg week_end "$WEEK_END" '
                [.data.search.nodes[] | select(.createdAt >= $week_start and .createdAt < $week_end)] | length
            ')
            echo "- **$week_reviews code reviews** completed, primarily in: $top_repos"
        fi

        if [[ "$total_prs" -gt 0 ]]; then
            local pr_titles
            pr_titles=$(echo "$created_prs" | jq -r '.[].title' | head -2)
            echo "- **$total_prs Pull Request(s) created:**"
            while IFS= read -r title; do
                echo "  - $title"
            done <<< "$pr_titles"
        fi

        # Add PRs in progress
        local active_prs_count
        active_prs_count=$(echo "$PRS_IN_PROGRESS" | grep "^ACTIVE_PR" | wc -l)
        if [[ "$active_prs_count" -gt 0 ]]; then
            echo "- **$active_prs_count PR(s) in progress with commits this week:**"
            echo "$PRS_IN_PROGRESS" | grep "^ACTIVE_PR" | while IFS='|' read -r prefix repo number title url created_at; do
                local commit_count
                commit_count=$(echo "$PRS_IN_PROGRESS" | grep -A 10 "ACTIVE_PR|$repo|$number" | grep "^COMMIT" | wc -l)
                echo "  - $title ($commit_count commits)"
            done
        fi

        if [[ "$total_issues" -gt 0 ]]; then
            local issue_titles
            issue_titles=$(echo "$created_issues" | jq -r '.[].title' | head -2)
            echo "- **$total_issues Issue(s) created:**"
            while IFS= read -r title; do
                echo "  - $title"
            done <<< "$issue_titles"
        fi
    fi

    # Documentation contributions
    if [[ -n "$documentation_contributions" ]]; then
        local doc_prs_count doc_issues_count doc_reviews_count
        doc_prs_count=$(echo "$documentation_contributions" | jq -r '.created_prs | length')
        doc_issues_count=$(echo "$documentation_contributions" | jq -r '.created_issues | length')
        doc_reviews_count=$(echo "$documentation_contributions" | jq -r '.reviewed_prs | length')

        local total_doc_work=$((doc_prs_count + doc_issues_count + doc_reviews_count))

        if [[ "$total_doc_work" -gt 0 ]]; then
            echo ""
            echo "### 📝 **Documentation & Content**"

            if [[ "$doc_prs_count" -gt 0 ]]; then
                local doc_pr_titles
                doc_pr_titles=$(echo "$documentation_contributions" | jq -r '.created_prs[].title' | head -3)
                echo "- **$doc_prs_count documentation PR(s) created:**"
                while IFS= read -r title; do
                    echo "  - $title"
                done <<< "$doc_pr_titles"
            fi

            if [[ "$doc_reviews_count" -gt 0 ]]; then
                echo "- **$doc_reviews_count documentation PR(s) reviewed**"
            fi

            if [[ "$doc_issues_count" -gt 0 ]]; then
                local doc_issue_titles
                doc_issue_titles=$(echo "$documentation_contributions" | jq -r '.created_issues[].title' | head -3)
                echo "- **$doc_issues_count documentation issue(s) created:**"
                while IFS= read -r title; do
                    echo "  - $title"
                done <<< "$doc_issue_titles"
            fi
        fi
    fi

    # Meeting highlights
    if [[ -n "$calendar_events" && "$calendar_events" != "1" ]]; then
        echo ""

        # Count total meetings for the week (simplified)
        local total_meetings total_meeting_hours
        total_meetings=$(echo "$calendar_events" | jq -r --arg week_start "$LAST_MONDAY" --arg week_end "$LAST_SUNDAY" '
            [.items[] |
            select(
                (.start.dateTime // .start.date | split("T")[0]) >= $week_start and
                (.start.dateTime // .start.date | split("T")[0]) <= $week_end
            ) |
            select((.summary | test("taking daughter|daycare|Writing|writing|busy|vaccuum|Home"; "i") | not)) |
            select(.eventType != "workingLocation") |
            select((.summary | test("ASYNC|office hours"; "i") | not)) |
            select(
                (.attendees | length) == 0 or
                (.attendees[] | select(.self == true) | .responseStatus | test("accepted|tentative"))
            )] | length
        ' 2>/dev/null)

        # Calculate total meeting time (fixed calculation)
        local total_minutes=0

        # Simple hour-based calculation for meetings with time
        local meetings_with_time
        meetings_with_time=$(echo "$calendar_events" | jq -r --arg week_start "$LAST_MONDAY" --arg week_end "$LAST_SUNDAY" '
            .items[] |
            select(
                (.start.dateTime // .start.date | split("T")[0]) >= $week_start and
                (.start.dateTime // .start.date | split("T")[0]) <= $week_end
            ) |
            select((.summary | test("taking daughter|daycare|Writing|writing|busy|vaccuum|Home"; "i") | not)) |
            select(.eventType != "workingLocation") |
            select((.summary | test("ASYNC|office hours"; "i") | not)) |
            select(
                (.attendees | length) == 0 or
                (.attendees[] | select(.self == true) | .responseStatus | test("accepted|tentative"))
            ) |
            if (.start.dateTime and .end.dateTime) then
                {
                    start: .start.dateTime,
                    end: .end.dateTime,
                    summary: .summary
                }
            else
                {
                    start: "all-day",
                    end: "all-day",
                    summary: .summary
                }
            end |
            "\(.start)|\(.end)|\(.summary)"
        ' 2>/dev/null)

        # Calculate duration for each meeting
        while IFS='|' read -r start_time end_time summary; do
            if [[ "$start_time" == "all-day" ]]; then
                total_minutes=$((total_minutes + 60))  # 1 hour default
            else
                # Simple time calculation - extract hours and minutes
                local start_hour start_min end_hour end_min
                start_hour=$(echo "$start_time" | sed 's/.*T\([0-9][0-9]\):.*/\1/')
                start_min=$(echo "$start_time" | sed 's/.*T[0-9][0-9]:\([0-9][0-9]\).*/\1/')
                end_hour=$(echo "$end_time" | sed 's/.*T\([0-9][0-9]\):.*/\1/')
                end_min=$(echo "$end_time" | sed 's/.*T[0-9][0-9]:\([0-9][0-9]\).*/\1/')

                if [[ "$start_hour" =~ ^[0-9]+$ ]] && [[ "$end_hour" =~ ^[0-9]+$ ]]; then
                    # Remove leading zeros to avoid octal interpretation
                    start_hour=$((10#$start_hour))
                    start_min=$((10#$start_min))
                    end_hour=$((10#$end_hour))
                    end_min=$((10#$end_min))

                    local start_total_min=$((start_hour * 60 + start_min))
                    local end_total_min=$((end_hour * 60 + end_min))
                    local duration=$((end_total_min - start_total_min))

                    # Handle negative duration (next day meetings)
                    if [[ "$duration" -lt 0 ]]; then
                        duration=$((duration + 1440))  # Add 24 hours
                    fi

                    # Reasonable bounds check (meetings shouldn't be more than 8 hours)
                    if [[ "$duration" -gt 0 ]] && [[ "$duration" -le 480 ]]; then
                        total_minutes=$((total_minutes + duration))
                    else
                        total_minutes=$((total_minutes + 60))  # Default 1 hour
                    fi
                else
                    total_minutes=$((total_minutes + 60))  # Default 1 hour
                fi
            fi
        done <<< "$meetings_with_time"

        total_meeting_hours=$(echo "$total_minutes" | awk '{printf "%.1f", $1/60}')

        echo "### 📅 **Meeting Highlights** ($total_meeting_hours hours)"

        echo "- **$total_meetings professional meetings** attended"

        # Highlight key meeting types (filtered by week range)
        local leadership_meetings team_meetings office_hours
        leadership_meetings=$(echo "$calendar_events" | jq -r --arg week_start "$LAST_MONDAY" --arg week_end "$LAST_SUNDAY" '
            [.items[] |
            select(
                (.start.dateTime // .start.date | split("T")[0]) >= $week_start and
                (.start.dateTime // .start.date | split("T")[0]) <= $week_end
            ) |
            select(.summary | test("leadership|sync|1:1|sprint"; "i")) |
            .summary] | length
        ' 2>/dev/null)

        office_hours=$(echo "$calendar_events" | jq -r --arg week_start "$LAST_MONDAY" --arg week_end "$LAST_SUNDAY" '
            [.items[] |
            select(
                (.start.dateTime // .start.date | split("T")[0]) >= $week_start and
                (.start.dateTime // .start.date | split("T")[0]) <= $week_end
            ) |
            select(.summary | test("office hours"; "i")) |
            .summary] | unique | length
        ' 2>/dev/null)

        team_meetings=$(echo "$calendar_events" | jq -r --arg week_start "$LAST_MONDAY" --arg week_end "$LAST_SUNDAY" '
            [.items[] |
            select(
                (.start.dateTime // .start.date | split("T")[0]) >= $week_start and
                (.start.dateTime // .start.date | split("T")[0]) <= $week_end
            ) |
            select(.summary | test("scrum|standup|retrospective|planning"; "i")) |
            .summary] | length
        ' 2>/dev/null)

        if [[ "$leadership_meetings" -gt 0 ]]; then
            echo "- **$leadership_meetings leadership/sync meetings** including 1:1s and team syncs"
        fi

        if [[ "$office_hours" -gt 0 ]]; then
            echo "- **$office_hours office hours sessions** hosted across different time zones"
        fi

        if [[ "$team_meetings" -gt 0 ]]; then
            echo "- **$team_meetings agile ceremonies** (standups, planning, retrospectives)"
        fi
    fi

    # Activity patterns
    # Claude work section
    if [[ -n "$CLAUDE_WORK_CATEGORIZATION" ]]; then
        echo ""
        echo "### 🤖 **AI-Assisted Development**"

        local pr_sessions exploratory_sessions
        pr_sessions=$(echo "$CLAUDE_WORK_CATEGORIZATION" | grep "^PR_RELATED" | cut -d'|' -f2)
        exploratory_sessions=$(echo "$CLAUDE_WORK_CATEGORIZATION" | grep "^EXPLORATORY" | cut -d'|' -f2)

        if [[ "$pr_sessions" -gt 0 ]] || [[ "$exploratory_sessions" -gt 0 ]]; then
            local total_sessions=$((pr_sessions + exploratory_sessions))
            echo "- **$total_sessions Claude sessions** estimated for the week"

            if [[ "$pr_sessions" -gt 0 ]]; then
                echo "  - $pr_sessions sessions on active PRs and implementation work"
            fi

            if [[ "$exploratory_sessions" -gt 0 ]]; then
                echo "  - $exploratory_sessions sessions on exploratory/research work"
            fi
        fi
    fi

    echo ""
    echo "### 📊 **Activity Patterns**"

    # Find most productive day (within the week range)
    local most_productive_day max_contributions
    most_productive_day=$(echo "$contrib_data" | jq -r --arg week_start "$LAST_MONDAY" --arg week_end "$LAST_SUNDAY" '
        .data.viewer.contributionsCollection.contributionCalendar.weeks[].contributionDays[] |
        select(.date >= $week_start and .date <= $week_end) |
        select(.contributionCount > 0) |
        {date: .date, count: .contributionCount} |
        [.count, .date] | @tsv
    ' | sort -nr | head -1 | cut -f2)

    max_contributions=$(echo "$contrib_data" | jq -r --arg week_start "$LAST_MONDAY" --arg week_end "$LAST_SUNDAY" '
        .data.viewer.contributionsCollection.contributionCalendar.weeks[].contributionDays[] |
        select(.date >= $week_start and .date <= $week_end) |
        select(.contributionCount > 0) |
        .contributionCount
    ' | sort -nr | head -1)

    if [[ -n "$most_productive_day" ]]; then
        local formatted_day
        if [[ "$OSTYPE" == "darwin"* ]]; then
            formatted_day=$(date -j -f "%Y-%m-%d" "$most_productive_day" +"%A" 2>/dev/null || echo "$most_productive_day")
        else
            formatted_day=$(date -d "$most_productive_day" +"%A" 2>/dev/null || echo "$most_productive_day")
        fi
        echo "- **Most productive day:** $formatted_day with $max_contributions GitHub contributions"
    fi

    # Analyze activity timing patterns from actual GitHub data
    echo "🔍 Analyzing activity timing patterns..." >&2
    local timing_analysis
    timing_analysis=$(fetch_activity_timing_patterns "$LAST_MONDAY" "$LAST_SUNDAY")

    if [[ -n "$timing_analysis" ]]; then
        echo "$timing_analysis"
    fi

    # Weekend activity check (within the week range)
    local weekend_contributions
    # Calculate Saturday date too
    local saturday_date
    if [[ "$OSTYPE" == "darwin"* ]]; then
        saturday_date=$(date -j -v+5d -f "%Y-%m-%d" "$LAST_MONDAY" +%Y-%m-%d 2>/dev/null)
    else
        saturday_date=$(date -d "$LAST_MONDAY + 5 days" +%Y-%m-%d 2>/dev/null)
    fi

    weekend_contributions=$(echo "$contrib_data" | jq -r --arg saturday "$saturday_date" --arg sunday "$LAST_SUNDAY" '
        .data.viewer.contributionsCollection.contributionCalendar.weeks[].contributionDays[] |
        select(.date == $saturday or .date == $sunday) |
        .contributionCount
    ' | awk '{sum += $1} END {print sum + 0}')

    if [[ "$weekend_contributions" -gt 0 ]]; then
        echo "- **Weekend contributions:** $weekend_contributions (shows dedication beyond regular hours)"
    else
        echo "- **Healthy work-life balance:** No weekend coding activity"
    fi

    echo ""
}

# Function to parse calendar events and group by day
parse_calendar_events() {
    local calendar_data="$1"
    local temp_file="/tmp/calendar_events_$$"

    # Parse calendar events into a temporary file for processing
    echo "$calendar_data" | jq -r '
    .items[] |
    {
        summary: .summary,
        start: (.start.dateTime // .start.date),
        end: (.end.dateTime // .end.date),
        eventType: .eventType,
        location: .location
    } |
    [.start, .summary, .eventType, (.location // ""), (.end // "")] | @tsv
    ' 2>/dev/null | sort > "$temp_file"

    if [[ ! -s "$temp_file" ]]; then
        echo "No calendar events found for this period."
        rm -f "$temp_file"
        return
    fi

    # Group events by date and format them
    local current_date=""
    while IFS=$'\t' read -r start_time summary event_type location end_time; do
        # Extract date from timestamp
        local event_date
        if [[ "$start_time" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
            # All-day event
            event_date="$start_time"
            local time_display="All day"
        else
            # Timed event - extract date and time
            event_date=$(echo "$start_time" | cut -d'T' -f1)
            local start_hour=$(date -j -f "%Y-%m-%dT%H:%M:%S%z" "$start_time" +"%H:%M" 2>/dev/null || echo "$start_time" | grep -o '[0-9][0-9]:[0-9][0-9]')
            local time_display="$start_hour"

            # Try to get end time for duration
            if [[ -n "$end_time" && "$end_time" != "null" ]]; then
                local end_hour=$(date -j -f "%Y-%m-%dT%H:%M:%S%z" "$end_time" +"%H:%M" 2>/dev/null || echo "$end_time" | grep -o '[0-9][0-9]:[0-9][0-9]')
                if [[ -n "$end_hour" && "$end_hour" != "$start_hour" ]]; then
                    time_display="$start_hour-$end_hour"
                fi
            fi
        fi

        # Print date header if it's a new date
        if [[ "$event_date" != "$current_date" ]]; then
            if [[ -n "$current_date" ]]; then
                echo ""
            fi

            # Format date nicely
            local formatted_date
            if [[ "$OSTYPE" == "darwin"* ]]; then
                formatted_date=$(date -j -f "%Y-%m-%d" "$event_date" +"%A, %B %d" 2>/dev/null || echo "$event_date")
            else
                formatted_date=$(date -d "$event_date" +"%A, %B %d" 2>/dev/null || echo "$event_date")
            fi
            echo "### 📅 $formatted_date"
            current_date="$event_date"
        fi

        # Clean up the summary and format the event
        local clean_summary=$(echo "$summary" | sed 's/^\[.*\] //g' | sed 's/^"//g' | sed 's/"$//g')

        # Add emoji based on event type or keywords
        local emoji="•"
        case "$event_type" in
            "workingLocation") emoji="🏠" ;;
            *)
                case "$clean_summary" in
                    *"meeting"*|*"Meeting"*|*"sync"*|*"Sync"*) emoji="🤝" ;;
                    *"interview"*|*"Interview"*) emoji="💼" ;;
                    *"lunch"*|*"Lunch"*|*"dinner"*|*"Dinner"*) emoji="🍽️" ;;
                    *"writing"*|*"Writing"*|*"blog"*|*"Blog"*) emoji="✍️" ;;
                    *"office hours"*|*"Office Hours"*) emoji="🏢" ;;
                    *"refinement"*|*"Refinement"*|*"planning"*|*"Planning"*) emoji="📋" ;;
                    *"training"*|*"Training"*|*"workshop"*|*"Workshop"*) emoji="🎓" ;;
                    *"daycare"*|*"school"*|*"family"*) emoji="👨‍👩‍👧‍👦" ;;
                    *"Home"*|*"home"*) emoji="🏠" ;;
                    *) emoji="📅" ;;
                esac
                ;;
        esac

        # Format location if present
        local location_text=""
        if [[ -n "$location" && "$location" != "null" && "$location" != "" ]]; then
            location_text=" @ $location"
        fi

        echo "- $emoji **$time_display** $clean_summary$location_text"

    done < "$temp_file"

    rm -f "$temp_file"
}

# Function to fetch detailed GitHub activity by day
fetch_detailed_github_activity() {
    local date="$1"
    echo "🔍 Fetching detailed GitHub activity for $date..." >&2

    # Get commits for the day
    local commits
    commits=$(gh api graphql -f query="
    {
      search(query: \"author:$GITHUB_USERNAME committer-date:$date\", type: COMMIT, first: 50) {
        nodes {
          ... on Commit {
            message
            repository {
              nameWithOwner
            }
            url
          }
        }
      }
    }" 2>/dev/null | jq -r '.data.search.nodes[] | "COMMIT|\(.repository.nameWithOwner)|\(.message | split("\n")[0])|\(.url)"' 2>/dev/null)

    # Get PR reviews for the day
    local reviews
    reviews=$(gh api graphql -f query="
    {
      search(query: \"reviewed-by:$GITHUB_USERNAME created:$date\", type: ISSUE, first: 50) {
        nodes {
          ... on PullRequest {
            title
            repository {
              nameWithOwner
            }
            number
            url
          }
        }
      }
    }" 2>/dev/null | jq -r '.data.search.nodes[] | "REVIEW|\(.repository.nameWithOwner)|\(.title)|\(.url)"' 2>/dev/null)

    # Combine and output
    {
        echo "$commits"
        echo "$reviews"
    } | grep -v "^$" 2>/dev/null || true
}

# Function to generate structured daily summary
generate_structured_daily_summary() {
    local contrib_data="$1"
    local calendar_events="$2"
    local created_prs="$3"
    local created_issues="$4"
    local reviewed_prs="$5"
    local claude_data="$6"

    echo "## 📊 Weekly Summary"
    echo ""

    # Create date range for the week
    local current_date="$LAST_MONDAY"
    local end_date="$LAST_SUNDAY"

    while [[ "$current_date" < "$end_date" ]] || [[ "$current_date" == "$end_date" ]]; do
        # Format date nicely
        local short_date day_of_week
        if [[ "$OSTYPE" == "darwin"* ]]; then
            short_date=$(date -j -f "%Y-%m-%d" "$current_date" +"%m/%d" 2>/dev/null || echo "$current_date")
            day_of_week=$(date -j -f "%Y-%m-%d" "$current_date" +"%A" 2>/dev/null || echo "")
        else
            short_date=$(date -d "$current_date" +"%m/%d" 2>/dev/null || echo "$current_date")
            day_of_week=$(date -d "$current_date" +"%A" 2>/dev/null || echo "")
        fi

        echo "- **$day_of_week $short_date:**"

        # Get GitHub contributions for this day
        local contributions
        contributions=$(echo "$contrib_data" | jq -r --arg date "$current_date" '
            .data.viewer.contributionsCollection.contributionCalendar.weeks[].contributionDays[] |
            select(.date == $date) | .contributionCount
        ' 2>/dev/null || echo "0")

        # GitHub activity section
        if [ "$contributions" -gt 0 ]; then
            echo "   - $contributions GitHub contributions"

            local item_count=1

            # PRs created on this day
            local day_prs
            day_prs=$(echo "$created_prs" | jq -r --arg date "$current_date" '
                .[] | select(.createdAt | startswith($date)) |
                "\(.repository.nameWithOwner)#\(.number): \(.title)"
            ' 2>/dev/null)

            if [[ -n "$day_prs" ]]; then
                while read -r pr; do
                    echo "     $item_count. PR: $pr"
                    ((item_count++))
                done <<< "$day_prs"
            fi

            # Issues created on this day
            local day_issues
            day_issues=$(echo "$created_issues" | jq -r --arg date "$current_date" '
                .[] | select(.createdAt | startswith($date)) |
                "\(.repository.nameWithOwner)#\(.number): \(.title)"
            ' 2>/dev/null)

            if [[ -n "$day_issues" ]]; then
                while read -r issue; do
                    echo "     $item_count. Issue: $issue"
                    ((item_count++))
                done <<< "$day_issues"
            fi

            # PRs reviewed on this day (top 3)
            local day_reviews
            day_reviews=$(echo "$reviewed_prs" | jq -r --arg date "$current_date" '
                .data.search.nodes[] |
                select(.createdAt | startswith($date)) |
                "\(.repository.nameWithOwner)#\(.number): \(.title)"
            ' 2>/dev/null | head -3)

            if [[ -n "$day_reviews" ]]; then
                while read -r review; do
                    echo "     $item_count. Reviewed: $review"
                    ((item_count++))
                done <<< "$day_reviews"
            fi

        else
            if [[ "$day_of_week" == "Saturday" || "$day_of_week" == "Sunday" ]]; then
                echo "   - Weekend - No GitHub activity"
            else
                echo "   - 0 GitHub contributions"
            fi
        fi

        # Calendar events section - only show meetings where attendance is required/accepted
        if [[ -n "$calendar_events" && "$calendar_events" != "1" ]]; then
            local meetings
            meetings=$(echo "$calendar_events" | jq -r --arg date "$current_date" --arg week_start "$LAST_MONDAY" --arg week_end "$LAST_SUNDAY" '
                [.items[] |
                select((.start.dateTime // .start.date) | startswith($date)) |
                select(
                    (.start.dateTime // .start.date | split("T")[0]) >= $week_start and
                    (.start.dateTime // .start.date | split("T")[0]) <= $week_end
                ) |
                # Filter out personal/declined events
                select((.summary | test("taking daughter|daycare|Writing|writing|busy|vaccuum|Home"; "i") | not)) |
                select(.eventType != "workingLocation") |
                select((.summary | test("ASYNC|office hours"; "i") | not)) |
                select(
                    (.attendees | length) == 0 or
                    (.attendees[] | select(.self == true) | .responseStatus | test("accepted|tentative"))
                ) |
                {
                    summary: .summary,
                    start: (.start.dateTime // .start.date),
                    eventType: .eventType,
                    description: (.description // ""),
                    responseStatus: (.attendees[]? | select(.self == true) | .responseStatus // "none")
                }] | length
            ' 2>/dev/null)

            if [[ "$meetings" -gt 0 ]]; then
                echo "   - $meetings required meetings"

                local meeting_count=1
                echo "$calendar_events" | jq -r --arg date "$current_date" --arg week_start "$LAST_MONDAY" --arg week_end "$LAST_SUNDAY" '
                    .items[] |
                    select((.start.dateTime // .start.date) | startswith($date)) |
                    select(
                        (.start.dateTime // .start.date | split("T")[0]) >= $week_start and
                        (.start.dateTime // .start.date | split("T")[0]) <= $week_end
                    ) |
                    # Apply same filters as above
                    select((.summary | test("taking daughter|daycare|Writing|writing|busy|vaccuum|Home"; "i") | not)) |
                    select(.eventType != "workingLocation") |
                    select((.summary | test("ASYNC|office hours"; "i") | not)) |
                    select(
                        (.attendees | length) == 0 or
                        (.attendees[] | select(.self == true) | .responseStatus | test("accepted|tentative"))
                    ) |
                    {
                        summary: .summary,
                        start: (.start.dateTime // .start.date),
                        responseStatus: (.attendees[]? | select(.self == true) | .responseStatus // "")
                    } |
                    if (.start | contains("T")) then
                        (.start | split("T")[1] | split("-")[0] | split("+")[0] | .[0:5]) + " - " + .summary +
                        (if .responseStatus == "tentative" then " (tentative)" else "" end)
                    else
                        "All day - " + .summary +
                        (if .responseStatus == "tentative" then " (tentative)" else "" end)
                    end
                ' 2>/dev/null | while read -r meeting; do
                    [[ -n "$meeting" ]] && echo "     $meeting_count. $meeting" && ((meeting_count++))
                done
            fi
        fi

        # Claude activity section
        local daily_claude_sessions
        daily_claude_sessions=$(echo "$CLAUDE_WORK_CATEGORIZATION" | awk -F'|' '
            BEGIN { pr_total=0; exp_total=0 }
            /^PR_RELATED/ { pr_total=$2 }
            /^EXPLORATORY/ { exp_total=$2 }
            END {
                daily_pr = int(pr_total/7)
                daily_exp = int(exp_total/7)
                if (daily_pr > 0 || daily_exp > 0) {
                    total = daily_pr + daily_exp
                    printf "   - ~%d Claude sessions (%d PR work, %d exploratory)", total, daily_pr, daily_exp
                }
            }
        ')

        if [[ -n "$daily_claude_sessions" ]]; then
            echo "$daily_claude_sessions"
        fi

        echo ""

        # Move to next day
        if [[ "$OSTYPE" == "darwin"* ]]; then
            current_date=$(date -j -f "%Y-%m-%d" -v+1d "$current_date" +%Y-%m-%d 2>/dev/null)
        else
            current_date=$(date -d "$current_date + 1 day" +%Y-%m-%d 2>/dev/null)
        fi
    done
}

# Function to generate the markdown report
generate_report() {
    local contrib_data="$1"
    local created_prs="$2"
    local created_issues="$3"
    local reviewed_prs="$4"
    local calendar_events="$5"
    local claude_data="$6"
    local prs_in_progress="$7"
    local claude_work_categorization="$8"
    local documentation_contributions="$9"

    # Make these available to the highlights function
    PRS_IN_PROGRESS="$prs_in_progress"
    CLAUDE_WORK_CATEGORIZATION="$claude_work_categorization"

    # Extract summary stats
    local total_contributions total_commits total_prs total_issues total_reviews
    total_contributions=$(echo "$contrib_data" | jq -r '.data.viewer.contributionsCollection.contributionCalendar.totalContributions')
    total_commits=$(echo "$contrib_data" | jq -r '.data.viewer.contributionsCollection.totalCommitContributions')
    total_prs=$(echo "$contrib_data" | jq -r '.data.viewer.contributionsCollection.totalPullRequestContributions')
    total_issues=$(echo "$contrib_data" | jq -r '.data.viewer.contributionsCollection.totalIssueContributions')
    total_reviews=$(echo "$contrib_data" | jq -r '.data.viewer.contributionsCollection.totalPullRequestReviewContributions')

    cat > "$OUTPUT_FILE" << EOF
# Weekly Review: $LAST_MONDAY to $LAST_SUNDAY

*Generated on $(date)*

$(generate_weekly_highlights "$contrib_data" "$created_prs" "$created_issues" "$reviewed_prs" "$calendar_events" "$documentation_contributions")

## 📊 GitHub Activity Summary

**Overall Contributions: $total_contributions total**
- **Commits**: $total_commits
- **Pull Requests Created**: $total_prs
- **Issues Created**: $total_issues
- **Pull Request Reviews**: $total_reviews

$(generate_structured_daily_summary "$contrib_data" "$calendar_events" "$created_prs" "$created_issues" "$reviewed_prs" "$claude_data")

### 🔧 Pull Requests You Created
EOF

    # Add created PRs
    if [ "$(echo "$created_prs" | jq length)" -gt 0 ]; then
        echo "$created_prs" | jq -r '.[] | "1. **[\(.repository.nameWithOwner)]** \"\(.title)\" (\(.createdAt | split("T")[0])) - \(.state)"' >> "$OUTPUT_FILE"
    else
        echo "*No pull requests created this week*" >> "$OUTPUT_FILE"
    fi

    cat >> "$OUTPUT_FILE" << EOF

### 🚧 Work in Progress
EOF

    # Add PRs in progress
    local active_prs_found=false
    if [[ -n "$PRS_IN_PROGRESS" ]]; then
        echo "$PRS_IN_PROGRESS" | grep "^ACTIVE_PR" | while IFS='|' read -r prefix repo number title url created_at; do
            if [[ "$active_prs_found" == "false" ]]; then
                active_prs_found=true
            fi

            local commit_count
            commit_count=$(echo "$PRS_IN_PROGRESS" | grep -A 20 "ACTIVE_PR|$repo|$number" | grep "^COMMIT" | wc -l)
            echo "1. **[$repo#$number]** \"$title\" ($commit_count commits this week)" >> "$OUTPUT_FILE"

            # Show recent commits
            echo "$PRS_IN_PROGRESS" | grep -A 20 "ACTIVE_PR|$repo|$number" | grep "^COMMIT" | head -3 | while IFS='|' read -r commit_prefix date oid message; do
                local short_date
                short_date=$(echo "$date" | cut -d'T' -f1 | cut -d'-' -f2,3 | tr '-' '/')
                echo "   - \`$oid\` $message ($short_date)" >> "$OUTPUT_FILE"
            done
        done

        if [[ $(echo "$PRS_IN_PROGRESS" | grep "^ACTIVE_PR" | wc -l) -eq 0 ]]; then
            echo "*No active work on existing PRs this week*" >> "$OUTPUT_FILE"
        fi
    else
        echo "*No active work on existing PRs this week*" >> "$OUTPUT_FILE"
    fi

    cat >> "$OUTPUT_FILE" << EOF

### 🐛 Issues You Created
EOF

    # Add created issues
    if [ "$(echo "$created_issues" | jq length)" -gt 0 ]; then
        echo "$created_issues" | jq -r '.[] | "1. **[\(.repository.nameWithOwner)]** \"\(.title)\" (\(.createdAt | split("T")[0])) - \(.state)"' >> "$OUTPUT_FILE"
    else
        echo "*No issues created this week*" >> "$OUTPUT_FILE"
    fi

    cat >> "$OUTPUT_FILE" << EOF

### 👀 Pull Requests You Reviewed
EOF

    # Add reviewed PRs
    local reviewed_count
    reviewed_count=$(echo "$reviewed_prs" | jq -r '.data.search.issueCount')

    if [ "$reviewed_count" -gt 0 ]; then
        echo "$reviewed_prs" | jq -r '.data.search.nodes[] | "1. **[\(.repository.nameWithOwner)]** \"\(.title)\" (\(.createdAt | split("T")[0])) - \(.state)"' >> "$OUTPUT_FILE"
    else
        echo "*No pull requests reviewed this week*" >> "$OUTPUT_FILE"
    fi

    # Add documentation contributions section
    cat >> "$OUTPUT_FILE" << EOF

### 📝 Documentation & Content Contributions
EOF

    # Count total documentation work
    local doc_prs_count doc_issues_count doc_reviews_count
    doc_prs_count=$(echo "$documentation_contributions" | jq -r '.created_prs | length')
    doc_issues_count=$(echo "$documentation_contributions" | jq -r '.created_issues | length')
    doc_reviews_count=$(echo "$documentation_contributions" | jq -r '.reviewed_prs | length')

    local total_doc_work=$((doc_prs_count + doc_issues_count + doc_reviews_count))

    if [[ "$total_doc_work" -gt 0 ]]; then
        if [[ "$doc_prs_count" -gt 0 ]]; then
            echo "" >> "$OUTPUT_FILE"
            echo "#### 🔧 Documentation PRs Created" >> "$OUTPUT_FILE"
            echo "$documentation_contributions" | jq -r '.created_prs[] | "1. **[\(.repository.nameWithOwner)]** \"\(.title)\" (\(.createdAt | split("T")[0])) - \(.state)"' >> "$OUTPUT_FILE"
        fi

        if [[ "$doc_reviews_count" -gt 0 ]]; then
            echo "" >> "$OUTPUT_FILE"
            echo "#### 👀 Documentation PRs Reviewed" >> "$OUTPUT_FILE"
            echo "$documentation_contributions" | jq -r '.reviewed_prs[] | "1. **[\(.repository.nameWithOwner)]** \"\(.title)\" (\(.createdAt | split("T")[0])) - \(.state)"' >> "$OUTPUT_FILE"
        fi

        if [[ "$doc_issues_count" -gt 0 ]]; then
            echo "" >> "$OUTPUT_FILE"
            echo "#### 🐛 Documentation Issues Created" >> "$OUTPUT_FILE"
            echo "$documentation_contributions" | jq -r '.created_issues[] | "1. **[\(.repository.nameWithOwner)]** \"\(.title)\" (\(.createdAt | split("T")[0])) - \(.state)"' >> "$OUTPUT_FILE"
        fi
    else
        echo "*No documentation contributions this week*" >> "$OUTPUT_FILE"
    fi


    # Add reflection section
    cat >> "$OUTPUT_FILE" << EOF

---

## 🎯 Weekly Reflection

### What went well this week?
*[Add your thoughts]*

### What could be improved?
*[Add your thoughts]*

### Key accomplishments
*[Add your thoughts]*

### Goals for next week
*[Add your thoughts]*

### Learning highlights
*[Add your thoughts]*

---

*This report was generated automatically by weekly-review.sh*
EOF
}

# Main execution
echo "🚀 Starting weekly review generation..."

# Fetch all data
CONTRIB_DATA=$(fetch_github_contributions)
CREATED_PRS=$(fetch_created_prs)
CREATED_ISSUES=$(fetch_created_issues)
REVIEWED_PRS=$(fetch_reviewed_prs)
PRS_IN_PROGRESS=$(fetch_prs_in_progress)
if [[ "$ENABLE_CALENDAR" == "true" ]]; then
    CALENDAR_EVENTS=$(fetch_calendar_events || echo "1")
else
    echo "📅 Calendar integration disabled in .env"
    CALENDAR_EVENTS="1"
fi
DOCUMENTATION_CONTRIBUTIONS=$(fetch_documentation_contributions)
if [[ "$ENABLE_CLAUDE_TRACKING" == "true" ]]; then
    CLAUDE_DATA=$(fetch_claude_conversation_activity || echo "{}")
    CLAUDE_WORK_CATEGORIZATION=$(categorize_claude_work "$CLAUDE_DATA" "$PRS_IN_PROGRESS")
else
    echo "🤖 Claude activity tracking disabled in .env"
    CLAUDE_DATA='{"sessions": 0, "pr_related": 0, "exploratory": 0}'
    CLAUDE_WORK_CATEGORIZATION='{"pr_work": 0, "exploratory_work": 0}'
fi

# Generate the report
generate_report "$CONTRIB_DATA" "$CREATED_PRS" "$CREATED_ISSUES" "$REVIEWED_PRS" "$CALENDAR_EVENTS" "$CLAUDE_DATA" "$PRS_IN_PROGRESS" "$CLAUDE_WORK_CATEGORIZATION" "$DOCUMENTATION_CONTRIBUTIONS"

echo "✅ Weekly review generated: $OUTPUT_FILE"
echo "📖 Open with: cat '$OUTPUT_FILE'"
echo "📝 Edit with: code '$OUTPUT_FILE'"

# Optionally open the file
if command -v code >/dev/null 2>&1; then
    read -p "Open in VS Code? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        code "$OUTPUT_FILE"
    fi
fi