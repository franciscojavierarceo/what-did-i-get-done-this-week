"""
Report readers for converting files back to WeeklyReport models
"""

import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, date

from .models import WeeklyReport, OutputFormat


class ReportReader(ABC):
    """Base class for report readers"""

    @abstractmethod
    def read(self, file_path: Path) -> WeeklyReport:
        """Read a report file and convert it back to WeeklyReport model"""
        pass

    @abstractmethod
    def can_read(self, file_path: Path) -> bool:
        """Check if this reader can handle the given file"""
        pass


class JSONReader(ReportReader):
    """Read JSON format reports"""

    def can_read(self, file_path: Path) -> bool:
        """Check if file is a JSON report"""
        return file_path.suffix.lower() == '.json'

    def read(self, file_path: Path) -> WeeklyReport:
        """Read JSON report file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            data = json.loads(content)
            try:
                # Try Pydantic v2 syntax first
                return WeeklyReport.model_validate(data)
            except AttributeError:
                # Fallback to Pydantic v1 syntax
                return WeeklyReport.parse_obj(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise ValueError(f"Could not parse JSON report {file_path}: {e}")


class MarkdownReader(ReportReader):
    """Read Markdown format reports"""

    def can_read(self, file_path: Path) -> bool:
        """Check if file is a Markdown report"""
        return file_path.suffix.lower() in ['.md', '.markdown']

    def read(self, file_path: Path) -> WeeklyReport:
        """Read Markdown report file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            return self._parse_markdown(content, file_path)
        except Exception as e:
            raise ValueError(f"Could not parse Markdown report {file_path}: {e}")

    def _parse_markdown(self, content: str, file_path: Path) -> WeeklyReport:
        """Parse Markdown content into WeeklyReport model"""
        # This is a simplified parser - in a full implementation,
        # you'd want more robust regex patterns and error handling

        # Extract title and date range
        title_match = re.search(r'# Weekly Review: (\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2})', content)
        if not title_match:
            raise ValueError("Could not find date range in Markdown title")

        start_date = date.fromisoformat(title_match.group(1))
        end_date = date.fromisoformat(title_match.group(2))

        # Extract generated timestamp
        generated_match = re.search(r'\*Generated on (.+?)\*', content)
        if generated_match:
            # Try to parse the timestamp (this is simplified - real implementation would be more robust)
            generated_at = datetime.now()  # Fallback to current time
        else:
            generated_at = datetime.now()

        # Extract basic stats from the content
        # Look for patterns like "**Overall Contributions: 25 total**"
        contributions_match = re.search(r'\*\*Overall Contributions: (\d+) total\*\*', content)
        total_contributions = int(contributions_match.group(1)) if contributions_match else 0

        # Extract PRs created
        prs_match = re.search(r'\*\*Pull Requests Created\*\*: (\d+)', content)
        total_prs_created = int(prs_match.group(1)) if prs_match else 0

        # Extract Issues created
        issues_match = re.search(r'\*\*Issues Created\*\*: (\d+)', content)
        total_issues_created = int(issues_match.group(1)) if issues_match else 0

        # Extract PR reviews
        reviews_match = re.search(r'\*\*Pull Request Reviews\*\*: (\d+)', content)
        total_prs_reviewed = int(reviews_match.group(1)) if reviews_match else 0

        # For a basic implementation, create a minimal WeeklyReport
        # In a full implementation, you'd extract all the detailed sections

        from .models import (
            DateRange, WeeklyStats, WeeklyHighlights, DailySummary
        )

        date_range = DateRange(start=start_date, end=end_date)

        stats = WeeklyStats(
            total_contributions=total_contributions,
            total_prs_created=total_prs_created,
            total_issues_created=total_issues_created,
            total_prs_reviewed=total_prs_reviewed,
            total_meetings=0,  # Would need to parse this from content
            total_meeting_hours=0.0,
            total_documentation_work=0,
            weekend_contributions=0
        )

        highlights = WeeklyHighlights(
            key_achievements=[],  # Would need to parse from ### Key Achievements section
            meeting_insights=[],
            documentation_summary=[],
            activity_patterns=[]
        )

        # Create minimal daily summaries
        daily_summaries: List[DailySummary] = []

        return WeeklyReport(
            date_range=date_range,
            generated_at=generated_at,
            stats=stats,
            highlights=highlights,
            daily_summaries=daily_summaries,
            documentation_contributions=[],
            metadata={"source_file": str(file_path), "format": "markdown"}
        )


class HTMLReader(ReportReader):
    """Read HTML format reports"""

    def can_read(self, file_path: Path) -> bool:
        """Check if file is an HTML report"""
        return file_path.suffix.lower() in ['.html', '.htm']

    def read(self, file_path: Path) -> WeeklyReport:
        """Read HTML report file"""
        # For now, raise an error since HTML parsing is complex
        # In a full implementation, you'd use BeautifulSoup or similar
        raise NotImplementedError(
            "HTML report reading is not yet implemented. "
            "Consider converting HTML reports to JSON or Markdown format first."
        )


def detect_format(file_path: Path) -> OutputFormat:
    """Auto-detect the format of a report file"""
    suffix = file_path.suffix.lower()

    if suffix == '.json':
        return OutputFormat.JSON
    elif suffix in ['.md', '.markdown']:
        return OutputFormat.MARKDOWN
    elif suffix in ['.html', '.htm']:
        return OutputFormat.HTML
    else:
        # Try to detect by content sniffing
        try:
            content = file_path.read_text(encoding='utf-8')[:1000]  # Read first 1KB

            if content.strip().startswith('{') and '"date_range"' in content:
                return OutputFormat.JSON
            elif content.startswith('# Weekly Review:') or '## Weekly Review:' in content:
                return OutputFormat.MARKDOWN
            elif content.startswith('<!DOCTYPE html') or '<html' in content:
                return OutputFormat.HTML
            else:
                raise ValueError(f"Could not detect format for {file_path}")

        except Exception as e:
            raise ValueError(f"Could not read or detect format for {file_path}: {e}")


def get_reader(file_path: Path) -> ReportReader:
    """Get the appropriate reader for a file"""
    # Try each reader in order of reliability
    readers = [JSONReader(), MarkdownReader(), HTMLReader()]

    for reader in readers:
        if reader.can_read(file_path):
            return reader

    raise ValueError(f"No suitable reader found for {file_path}")


def read_report(file_path: Path) -> WeeklyReport:
    """Read a report file and return a WeeklyReport model

    This is the main entry point for reading reports.
    It auto-detects the format and uses the appropriate reader.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Report file not found: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    reader = get_reader(file_path)
    return reader.read(file_path)