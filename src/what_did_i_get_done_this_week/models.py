"""
Data models for the weekly review system
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class OutputFormat(str, Enum):
    """Supported output formats"""
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"


class DateRange(BaseModel):
    """Date range for a weekly period"""
    start: date
    end: date

    @property
    def week_label(self) -> str:
        """Get ISO week label (e.g., '2024-W13')"""
        year, week, _ = self.start.isocalendar()
        return f"{year}-W{week:02d}"


class GitHubContribution(BaseModel):
    """A single GitHub contribution"""
    date: date
    count: int
    url: Optional[str] = None


class GitHubPullRequest(BaseModel):
    """GitHub Pull Request data"""
    number: int
    title: str
    url: str
    repository: str
    state: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    author: str
    is_draft: bool = False


class GitHubIssue(BaseModel):
    """GitHub Issue data"""
    number: int
    title: str
    url: str
    repository: str
    state: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    author: str


class GitHubReview(BaseModel):
    """GitHub PR Review data"""
    pull_request: GitHubPullRequest
    state: str  # APPROVED, CHANGES_REQUESTED, COMMENTED
    submitted_at: datetime


class CalendarEvent(BaseModel):
    """Calendar event data"""
    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    is_all_day: bool = False
    attendees_count: Optional[int] = None
    response_status: Optional[str] = None  # accepted, tentative, declined
    event_type: Optional[str] = None
    description: Optional[str] = None


class ClaudeSession(BaseModel):
    """Claude AI session data"""
    date: date
    estimated_sessions: int
    categories: Dict[str, int] = Field(default_factory=dict)  # pr_work, exploratory, etc.


class DocumentationContribution(BaseModel):
    """Documentation contribution tracking"""
    title: str
    url: str
    repository: str
    type: str  # pr, issue, review
    created_at: datetime
    is_blog_post: bool = False
    is_readme: bool = False


class WeeklyStats(BaseModel):
    """Weekly statistics summary"""
    total_contributions: int
    total_prs_created: int
    total_issues_created: int
    total_prs_reviewed: int
    total_meetings: int
    total_meeting_hours: float
    total_documentation_work: int
    most_productive_day: Optional[date] = None
    weekend_contributions: int


class WeeklyHighlights(BaseModel):
    """Weekly highlights and key achievements"""
    key_achievements: List[str]
    meeting_insights: List[str]
    documentation_summary: List[str]
    activity_patterns: List[str]


class DailySummary(BaseModel):
    """Summary for a single day"""
    date: date
    day_name: str
    contributions: List[GitHubContribution]
    prs_created: List[GitHubPullRequest]
    issues_created: List[GitHubIssue]
    reviews_completed: List[GitHubReview]
    meetings: List[CalendarEvent]
    claude_sessions: Optional[ClaudeSession] = None


class WeeklyReport(BaseModel):
    """Complete weekly report data"""
    date_range: DateRange
    generated_at: datetime
    stats: WeeklyStats
    highlights: WeeklyHighlights
    daily_summaries: List[DailySummary]
    documentation_contributions: List[DocumentationContribution]
    created_prs: List[GitHubPullRequest] = Field(default_factory=list)
    created_issues: List[GitHubIssue] = Field(default_factory=list)
    reviewed_prs: List[GitHubPullRequest] = Field(default_factory=list)
    claude_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }