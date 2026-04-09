"""
Output formatters for weekly reports
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from .models import WeeklyReport, DailySummary, CalendarEvent


class ReportFormatter(ABC):
    """Base class for report formatters"""

    @abstractmethod
    def format(self, report: WeeklyReport) -> str:
        """Format the report into a string"""
        pass


class MarkdownFormatter(ReportFormatter):
    """Format reports as Markdown"""

    def format(self, report: WeeklyReport) -> str:
        """Generate beautiful Markdown report"""
        lines = []

        is_daily = report.date_range.start == report.date_range.end
        duration_days = (report.date_range.end - report.date_range.start).days + 1
        is_monthly = duration_days > 14

        if is_daily:
            date_label = report.date_range.start.strftime("%m/%d/%y")
            period_type = "Daily"
        elif is_monthly:
            period_type = "Monthly"
        else:
            period_type = "Weekly"

        # Header
        if is_daily:
            lines.append(f"# {date_label} Review")
        else:
            lines.append(f"# {period_type} Review: {report.date_range.start} to {report.date_range.end}")
        lines.append("")
        lines.append(f"*Generated on {report.generated_at.strftime('%a %b %d %H:%M:%S %Z %Y')}*")
        lines.append("")

        # Highlights
        lines.append(f"## 🌟 {date_label + ' ' if is_daily else period_type + ' '}Highlights")
        lines.append("")

        # Key Achievements
        lines.append("### 🎯 **Key Achievements**")
        for achievement in report.highlights.key_achievements:
            if achievement:
                lines.append(f"- **{achievement}**")
        lines.append("")

        # Documentation
        if report.highlights.documentation_summary:
            lines.append("### 📝 **Documentation & Content**")
            for doc_item in report.highlights.documentation_summary:
                if doc_item:
                    lines.append(f"- **{doc_item}**")
            lines.append("")

        # Meeting Highlights
        if report.highlights.meeting_insights:
            lines.append(f"### 📅 **Meeting Highlights** ({report.stats.total_meeting_hours:.1f} hours)")
            for meeting_item in report.highlights.meeting_insights:
                if meeting_item:
                    lines.append(f"- **{meeting_item}**")
            lines.append("")

        # Vibe Engineering
        if report.claude_data and report.claude_data.get("total_sessions", 0) > 0:
            total = report.claude_data["total_sessions"]
            lines.append("### 🤖 **Vibe Engineering**")
            lines.append(f"- **{total} Claude session{'s' if total != 1 else ''}** estimated from shell history")
            lines.append("")

        # Activity Patterns
        if report.highlights.activity_patterns:
            lines.append("### 📊 **Activity Patterns**")
            for pattern in report.highlights.activity_patterns:
                if pattern:
                    lines.append(f"- **{pattern}**")
            lines.append("")

        # GitHub Activity Summary
        lines.append("## 📊 GitHub Activity Summary")
        lines.append("")
        lines.append(f"**Overall Contributions: {report.stats.total_contributions} total**")
        lines.append(f"- **Pull Requests Created**: {report.stats.total_prs_created}")
        lines.append(f"- **Issues Created**: {report.stats.total_issues_created}")
        lines.append(f"- **Pull Request Reviews**: {report.stats.total_prs_reviewed}")
        lines.append("")

        # PRs Created (detailed)
        if report.created_prs:
            lines.append("### 🔧 Pull Requests Created")
            for i, pr in enumerate(report.created_prs, 1):
                date_str = pr.created_at.strftime("%Y-%m-%d")
                state = pr.state.lower()
                lines.append(f"{i}. **[{pr.repository}#{pr.number}]({pr.url})** \"{pr.title}\" ({date_str}, {state})")
            lines.append("")

        # Issues Created (detailed)
        if report.created_issues:
            lines.append("### 🐛 Issues Created")
            for i, issue in enumerate(report.created_issues, 1):
                date_str = issue.created_at.strftime("%Y-%m-%d")
                state = issue.state.lower()
                lines.append(f"{i}. **[{issue.repository}#{issue.number}]({issue.url})** \"{issue.title}\" ({date_str}, {state})")
            lines.append("")

        # PRs Reviewed (detailed, excluding doc reviews already shown below)
        non_doc_reviews = [pr for pr in report.reviewed_prs
                          if not any(d.url == pr.url for d in report.documentation_contributions)]
        if non_doc_reviews:
            lines.append("### 👀 Pull Requests Reviewed")
            for i, pr in enumerate(non_doc_reviews, 1):
                state = pr.state.lower()
                lines.append(f"{i}. **[{pr.repository}#{pr.number}]({pr.url})** \"{pr.title}\" by @{pr.author} ({state})")
            lines.append("")

        # Meetings (for daily reports, show inline; for weekly, show in daily breakdown)
        if is_daily:
            all_meetings = [m for daily in report.daily_summaries for m in daily.meetings]
            if all_meetings:
                lines.append(f"### 📅 Meetings ({len(all_meetings)})")
                for i, meeting in enumerate(all_meetings, 1):
                    time_str = self._format_meeting_time(meeting)
                    lines.append(f"{i}. {time_str} - {meeting.title}")
                lines.append("")

        # Daily Breakdown
        if not is_daily:
            lines.append(f"## 📊 {period_type} Summary")
            lines.append("")

            for daily in report.daily_summaries:
                if any(c.count > 0 for c in daily.contributions) or daily.meetings:
                    # Day header
                    emoji = self._get_day_emoji(daily.day_name)
                    short_date = daily.date.strftime("%m/%d")
                    lines.append(f"- **{emoji} {daily.day_name} {short_date}:**")

                    # GitHub contributions
                    total_day_contributions = sum(c.count for c in daily.contributions)
                    if total_day_contributions > 0:
                        lines.append(f"   - {total_day_contributions} GitHub contributions")

                    # Meetings
                    if daily.meetings:
                        lines.append(f"   - {len(daily.meetings)} required meetings")
                        for i, meeting in enumerate(daily.meetings[:10], 1):  # Limit to 10
                            time_str = self._format_meeting_time(meeting)
                            lines.append(f"     {i}. {time_str} - {meeting.title}")

                    lines.append("")

        # Documentation Contributions
        if report.documentation_contributions:
            lines.append("### 📝 Documentation & Content Contributions")
            lines.append("")

            # Group by type
            prs = [d for d in report.documentation_contributions if d.type == "pr"]
            reviews = [d for d in report.documentation_contributions if d.type == "review"]
            issues = [d for d in report.documentation_contributions if d.type == "issue"]

            if prs:
                lines.append("#### 🔧 Documentation PRs Created")
                for i, pr in enumerate(prs, 1):
                    date_str = pr.created_at.strftime("%Y-%m-%d")
                    lines.append(f"{i}. **[{pr.repository}]** \"{pr.title}\" ({date_str})")
                lines.append("")

            if reviews:
                lines.append("#### 👀 Documentation PRs Reviewed")
                for i, review in enumerate(reviews, 1):
                    date_str = review.created_at.strftime("%Y-%m-%d")
                    lines.append(f"{i}. **[{review.repository}]** \"{review.title}\" ({date_str})")
                lines.append("")

            if issues:
                lines.append("#### 🐛 Documentation Issues Created")
                for i, issue in enumerate(issues, 1):
                    date_str = issue.created_at.strftime("%Y-%m-%d")
                    lines.append(f"{i}. **[{issue.repository}]** \"{issue.title}\" ({date_str})")
                lines.append("")

        # Reflection
        lines.append("---")
        lines.append("")
        lines.append(f"## 🎯 {period_type} Reflection")
        lines.append("")
        lines.append("### What could I have done better?")
        lines.append("*[Add your thoughts]*")
        lines.append("")
        lines.append("### What is important that I am missing?")
        lines.append("*[Add your thoughts]*")
        lines.append("")
        lines.append("### Am I doing work that is aligned with my goals?")
        lines.append("*[Add your thoughts]*")
        lines.append("")
        lines.append("### How do I feel?")
        lines.append("*[Add your thoughts]*")
        lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*This report was generated automatically by what-did-i-get-done-this-week v2.0*")

        return "\n".join(lines)

    def _get_day_emoji(self, day_name: str) -> str:
        """Get emoji for day of week"""
        emoji_map = {
            "Monday": "🌟",
            "Tuesday": "🚀",
            "Wednesday": "⚡",
            "Thursday": "🎯",
            "Friday": "🎉",
            "Saturday": "🌅",
            "Sunday": "🌙"
        }
        return emoji_map.get(day_name, "📅")

    def _format_meeting_time(self, meeting: CalendarEvent) -> str:
        """Format meeting time for display"""
        if meeting.is_all_day:
            return "All day"
        elif meeting.start_time:
            return meeting.start_time.strftime("%H:%M")
        else:
            return "TBD"


class HTMLFormatter(ReportFormatter):
    """Format reports as HTML"""

    def format(self, report: WeeklyReport) -> str:
        """Generate HTML report"""
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Weekly Review: {report.date_range.start} to {report.date_range.end}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
                .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
                .stat-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .highlight {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 10px 0; }}
                .day-section {{ margin: 15px 0; padding: 15px; border-left: 4px solid #007bff; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Weekly Review: {report.date_range.start} to {report.date_range.end}</h1>
                    <p><em>Generated on {report.generated_at.strftime('%B %d, %Y at %H:%M')}</em></p>
                </div>

                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-value">{report.stats.total_contributions}</div>
                        <div>GitHub Contributions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{report.stats.total_prs_reviewed}</div>
                        <div>Code Reviews</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{report.stats.total_meetings}</div>
                        <div>Meetings</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{report.stats.total_documentation_work}</div>
                        <div>Documentation Work</div>
                    </div>
                </div>

                <h2>🌟 Weekly Highlights</h2>
                {"".join(f'<div class="highlight">{achievement}</div>' for achievement in report.highlights.key_achievements if achievement)}

                <h2>📊 Daily Breakdown</h2>
                {"".join(self._format_daily_html(daily) for daily in report.daily_summaries if any(c.count > 0 for c in daily.contributions) or daily.meetings)}
            </div>
        </body>
        </html>
        """
        return html

    def _format_daily_html(self, daily: DailySummary) -> str:
        """Format a daily summary as HTML"""
        total_contributions = sum(c.count for c in daily.contributions)
        meeting_count = len(daily.meetings)

        return f"""
        <div class="day-section">
            <h3>{daily.day_name} {daily.date.strftime('%m/%d')}</h3>
            {f'<p><strong>{total_contributions}</strong> GitHub contributions</p>' if total_contributions > 0 else ''}
            {f'<p><strong>{meeting_count}</strong> meetings attended</p>' if meeting_count > 0 else ''}
        </div>
        """


class JSONFormatter(ReportFormatter):
    """Format reports as JSON"""

    def format(self, report: WeeklyReport) -> str:
        """Generate JSON report"""
        try:
            # Try Pydantic v2 syntax first
            return report.model_dump_json(indent=2)
        except AttributeError:
            # Fallback to Pydantic v1 syntax
            return report.json(indent=2)