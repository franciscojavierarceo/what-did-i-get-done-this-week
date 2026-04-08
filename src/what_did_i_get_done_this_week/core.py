"""
Core weekly review generation engine
"""

import subprocess
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from .models import (
    DateRange, GitHubContribution, GitHubPullRequest, GitHubIssue,
    CalendarEvent, ClaudeSession, WeeklyReport, WeeklyStats,
    WeeklyHighlights, DailySummary, DocumentationContribution,
    OutputFormat
)
from .config import Config
from .formatters import MarkdownFormatter, HTMLFormatter, JSONFormatter


class WeeklyReviewGenerator:
    """Main class for generating weekly reviews"""

    def __init__(self, config: Config):
        self.config = config

    def fetch_github_contributions(self, date_range: DateRange) -> List[GitHubContribution]:
        """Fetch GitHub contributions for the date range"""
        query = f"""
        {{
          viewer {{
            contributionsCollection(
              from: "{date_range.start.isoformat()}T00:00:00Z"
              to: "{date_range.end.isoformat()}T23:59:59Z"
            ) {{
              contributionCalendar {{
                totalContributions
                weeks {{
                  contributionDays {{
                    date
                    contributionCount
                  }}
                }}
              }}
            }}
          }}
        }}
        """

        try:
            result = subprocess.run(
                ["gh", "api", "graphql", "-f", f"query={query}"],
                capture_output=True,
                text=True,
                check=True
            )

            data = json.loads(result.stdout)
            contributions = []

            for week in data["data"]["viewer"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
                for day in week["contributionDays"]:
                    date_obj = datetime.fromisoformat(day["date"]).date()
                    if date_range.start <= date_obj <= date_range.end:
                        contributions.append(GitHubContribution(
                            date=date_obj,
                            count=day["contributionCount"]
                        ))

            return contributions

        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
            raise RuntimeError(f"Failed to fetch GitHub contributions: {e}")

    def fetch_prs_and_issues(self, date_range: DateRange) -> Dict[str, Any]:
        """Fetch PRs created, issues created, and PRs reviewed"""
        start_str = date_range.start.isoformat()
        end_str = date_range.end.isoformat()

        try:
            # PRs created
            created_prs_result = subprocess.run([
                "gh", "search", "prs",
                "--author", self.config.github_username,
                "--created", f"{start_str}..{end_str}",
                "--json", "title,url,repository,createdAt,state,number,author"
            ], capture_output=True, text=True, check=True)

            # Issues created
            created_issues_result = subprocess.run([
                "gh", "search", "issues",
                "--author", self.config.github_username,
                "--created", f"{start_str}..{end_str}",
                "--json", "title,url,repository,createdAt,state,number,author"
            ], capture_output=True, text=True, check=True)

            # PRs reviewed (using GraphQL for better data)
            review_query = f"""
            {{
              search(
                query: "reviewed-by:{self.config.github_username} updated:{start_str}..{end_str}"
                type: ISSUE
                first: 100
              ) {{
                nodes {{
                  ... on PullRequest {{
                    title
                    url
                    number
                    repository {{
                      nameWithOwner
                    }}
                    createdAt
                    state
                    author {{
                      login
                    }}
                  }}
                }}
              }}
            }}
            """

            reviewed_prs_result = subprocess.run([
                "gh", "api", "graphql", "-f", f"query={review_query}"
            ], capture_output=True, text=True, check=True)

            # Parse results
            created_prs = json.loads(created_prs_result.stdout)
            created_issues = json.loads(created_issues_result.stdout)
            reviewed_prs = json.loads(reviewed_prs_result.stdout)

            return {
                "created_prs": created_prs,
                "created_issues": created_issues,
                "reviewed_prs": reviewed_prs
            }

        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to fetch PRs and issues: {e}")

    def fetch_calendar_events(self, date_range: DateRange) -> Optional[List[CalendarEvent]]:
        """Fetch calendar events using Google Workspace CLI"""
        if not self.config.enable_calendar:
            return None

        start_datetime = f"{date_range.start.isoformat()}T00:00:00Z"
        end_datetime = f"{date_range.end.isoformat()}T23:59:59Z"

        try:
            result = subprocess.run([
                "gws", "calendar", "events", "list",
                "--params", json.dumps({
                    "calendarId": "primary",
                    "timeMin": start_datetime,
                    "timeMax": end_datetime,
                    "maxResults": 100,
                    "singleEvents": True,
                    "orderBy": "startTime"
                }),
                "--format", "json"
            ], capture_output=True, text=True, check=True)

            data = json.loads(result.stdout)
            events = []

            for item in data.get("items", []):
                # Skip personal events and working location markers
                summary = item.get("summary", "")
                if any(skip_word in summary.lower() for skip_word in [
                    "daycare", "writing", "busy", "vaccuum", "home", "daughter"
                ]):
                    continue

                if item.get("eventType") == "workingLocation":
                    continue

                # Skip async meetings and office hours
                if any(skip_pattern in summary.lower() for skip_pattern in [
                    "async", "office hours"
                ]):
                    continue

                # Check attendance status
                attendees = item.get("attendees", [])
                if attendees:
                    user_response = None
                    for attendee in attendees:
                        if attendee.get("self"):
                            user_response = attendee.get("responseStatus")
                            break

                    # Only include accepted or tentative meetings
                    if user_response not in ["accepted", "tentative"]:
                        continue

                # Parse start/end times
                start_time = None
                end_time = None
                is_all_day = False

                if "dateTime" in item.get("start", {}):
                    start_time = datetime.fromisoformat(
                        item["start"]["dateTime"].replace("Z", "+00:00")
                    )
                elif "date" in item.get("start", {}):
                    start_time = datetime.fromisoformat(item["start"]["date"])
                    is_all_day = True

                if "dateTime" in item.get("end", {}):
                    end_time = datetime.fromisoformat(
                        item["end"]["dateTime"].replace("Z", "+00:00")
                    )
                elif "date" in item.get("end", {}):
                    end_time = datetime.fromisoformat(item["end"]["date"])

                events.append(CalendarEvent(
                    title=summary,
                    start_time=start_time,
                    end_time=end_time,
                    is_all_day=is_all_day,
                    attendees_count=len(attendees),
                    response_status=user_response,
                    event_type=item.get("eventType"),
                    description=item.get("description")
                ))

            return events

        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            # Calendar integration is optional, don't fail the whole process
            return None

    def estimate_claude_activity(self, date_range: DateRange) -> Optional[Dict[str, Any]]:
        """Estimate Claude AI usage during the week"""
        if not self.config.enable_claude_tracking:
            return None

        # This is a simplified estimation - in practice you'd want more sophisticated tracking
        estimated_sessions = 0
        daily_breakdown = {}

        # Check shell history for Claude-related commands
        try:
            zsh_history = Path.home() / ".zsh_history"
            if zsh_history.exists():
                with open(zsh_history, 'r', errors='ignore') as f:
                    lines = f.readlines()

                claude_commands = [
                    line for line in lines
                    if any(keyword in line.lower() for keyword in ['claude', 'anthropic'])
                ]
                estimated_sessions = len(claude_commands)

        except Exception:
            pass  # Shell history access is optional

        # Estimate sessions per day (rough heuristic)
        days_in_range = (date_range.end - date_range.start).days + 1
        sessions_per_day = estimated_sessions / days_in_range if days_in_range > 0 else 0

        current_date = date_range.start
        while current_date <= date_range.end:
            # Weekdays get more sessions than weekends
            multiplier = 1.0 if current_date.weekday() < 5 else 0.3
            daily_sessions = int(sessions_per_day * multiplier)

            daily_breakdown[current_date.isoformat()] = {
                "sessions": daily_sessions,
                "pr_related": int(daily_sessions * 0.6),  # 60% PR-related
                "exploratory": int(daily_sessions * 0.4),  # 40% exploratory
            }

            current_date += timedelta(days=1)

        return {
            "total_sessions": estimated_sessions,
            "daily_breakdown": daily_breakdown,
            "estimation_method": "shell_history_heuristic"
        }

    def identify_documentation_contributions(
        self,
        prs_issues_data: Dict[str, Any]
    ) -> List[DocumentationContribution]:
        """Identify documentation-related contributions"""
        doc_contributions = []

        # Check created PRs for documentation
        for pr in prs_issues_data["created_prs"]:
            title = pr["title"].lower()
            if any(keyword in title for keyword in [
                "docs:", "documentation", "blog", "readme", "tutorial", "guide"
            ]):
                doc_contributions.append(DocumentationContribution(
                    title=pr["title"],
                    url=pr["url"],
                    repository=pr["repository"]["nameWithOwner"],
                    type="pr",
                    created_at=datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00")),
                    is_blog_post="blog" in title,
                    is_readme="readme" in title,
                ))

        # Check created issues for documentation
        for issue in prs_issues_data["created_issues"]:
            title = issue["title"].lower()
            if any(keyword in title for keyword in [
                "docs:", "documentation", "blog", "readme", "tutorial", "guide"
            ]):
                doc_contributions.append(DocumentationContribution(
                    title=issue["title"],
                    url=issue["url"],
                    repository=issue["repository"]["nameWithOwner"],
                    type="issue",
                    created_at=datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00")),
                    is_blog_post="blog" in title,
                    is_readme="readme" in title,
                ))

        # Check reviewed PRs for documentation
        for pr_node in prs_issues_data["reviewed_prs"]["data"]["search"]["nodes"]:
            title = pr_node["title"].lower()
            if any(keyword in title for keyword in [
                "docs:", "documentation", "blog", "readme", "tutorial", "guide"
            ]):
                doc_contributions.append(DocumentationContribution(
                    title=pr_node["title"],
                    url=pr_node["url"],
                    repository=pr_node["repository"]["nameWithOwner"],
                    type="review",
                    created_at=datetime.fromisoformat(pr_node["createdAt"].replace("Z", "+00:00")),
                    is_blog_post="blog" in title,
                    is_readme="readme" in title,
                ))

        return doc_contributions

    def generate_report(
        self,
        date_range: DateRange,
        contributions: List[GitHubContribution],
        prs_issues: Dict[str, Any],
        calendar_data: Optional[List[CalendarEvent]] = None,
        claude_data: Optional[Dict[str, Any]] = None,
        output_format: str = "markdown"
    ) -> str:
        """Generate the complete weekly report"""

        # Calculate stats
        total_contributions = sum(c.count for c in contributions)
        total_prs_created = len(prs_issues["created_prs"])
        total_issues_created = len(prs_issues["created_issues"])
        total_prs_reviewed = len(prs_issues["reviewed_prs"]["data"]["search"]["nodes"])

        # Meeting stats
        total_meetings = len(calendar_data) if calendar_data else 0
        total_meeting_hours = 0.0
        if calendar_data:
            for event in calendar_data:
                if event.start_time and event.end_time and not event.is_all_day:
                    duration = (event.end_time - event.start_time).total_seconds() / 3600
                    total_meeting_hours += duration

        # Find most productive day
        most_productive_day = None
        max_contributions = 0
        for contrib in contributions:
            if contrib.count > max_contributions:
                max_contributions = contrib.count
                most_productive_day = contrib.date

        # Weekend contributions
        weekend_contributions = sum(
            c.count for c in contributions
            if c.date.weekday() in [5, 6]  # Saturday, Sunday
        )

        # Documentation contributions
        doc_contributions = self.identify_documentation_contributions(prs_issues)

        stats = WeeklyStats(
            total_contributions=total_contributions,
            total_prs_created=total_prs_created,
            total_issues_created=total_issues_created,
            total_prs_reviewed=total_prs_reviewed,
            total_meetings=total_meetings,
            total_meeting_hours=total_meeting_hours,
            total_documentation_work=len(doc_contributions),
            most_productive_day=most_productive_day,
            weekend_contributions=weekend_contributions,
        )

        # Generate highlights
        is_daily = date_range.start == date_range.end
        period_label = "today" if is_daily else "across the week"
        key_achievements = [
            f"{total_contributions} GitHub contributions {period_label}",
            f"{total_prs_reviewed} code reviews completed",
        ]
        if total_prs_created > 0:
            key_achievements.append(f"{total_prs_created} Pull Request(s) created")
        if doc_contributions:
            key_achievements.append(f"{len(doc_contributions)} documentation contributions")

        highlights = WeeklyHighlights(
            key_achievements=key_achievements,
            meeting_insights=[
                f"{total_meetings} professional meetings attended",
                f"{total_meeting_hours:.1f} hours in meetings",
            ] if calendar_data else [],
            documentation_summary=[
                f"{len([d for d in doc_contributions if d.is_blog_post])} blog post(s)",
                f"{len([d for d in doc_contributions if d.type == 'review'])} documentation PR(s) reviewed",
            ] if doc_contributions else [],
            activity_patterns=[] if is_daily else [
                pattern for pattern in [
                    f"Most productive day: {most_productive_day.strftime('%A')} with {max_contributions} contributions" if most_productive_day else None,
                    f"Weekend contributions: {weekend_contributions}" if weekend_contributions > 0 else "Work-life balance: No weekend coding",
                ] if pattern is not None
            ]
        )

        # Generate daily summaries (simplified for now)
        daily_summaries = []
        current_date = date_range.start
        while current_date <= date_range.end:
            day_contributions = [c for c in contributions if c.date == current_date]
            day_meetings = [e for e in (calendar_data or []) if e.start_time.date() == current_date]

            daily_summaries.append(DailySummary(
                date=current_date,
                day_name=current_date.strftime("%A"),
                contributions=day_contributions,
                prs_created=[],  # TODO: Filter by date
                issues_created=[],  # TODO: Filter by date
                reviews_completed=[],  # TODO: Filter by date
                meetings=day_meetings,
            ))

            current_date += timedelta(days=1)

        # Create the report
        report = WeeklyReport(
            date_range=date_range,
            generated_at=datetime.now(),
            stats=stats,
            highlights=highlights,
            daily_summaries=daily_summaries,
            documentation_contributions=doc_contributions,
            metadata={
                "generator": "what-did-i-get-done-this-week-v2",
                "github_username": self.config.github_username,
            }
        )

        # Format output
        if output_format == OutputFormat.MARKDOWN:
            formatter = MarkdownFormatter()
        elif output_format == OutputFormat.HTML:
            formatter = HTMLFormatter()
        elif output_format == OutputFormat.JSON:
            formatter = JSONFormatter()
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        return formatter.format(report)