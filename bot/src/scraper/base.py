"""
Base abstractions and data structures for job discovery.
"""
from dataclasses import dataclass
from typing import Optional
from abc import ABC, abstractmethod

@dataclass
class JobItem:
    jobname: str
    company: str
    link: str
    source: str = "web"
    salary: Optional[str] = None
    location: Optional[str] = "Baku, Azerbaijan"
    posted_date: Optional[str] = None
    feed_index: int = 0

    def is_valid(self) -> bool:
        """Basic validation to ensure required fields are present."""
        if not self.jobname or not self.company or not self.link:
            return False
        if not self.link.startswith("http://") and not self.link.startswith("https://"):
            return False
        return True

    def get_sort_key(self) -> float:
        """
        Calculates a sort score where lower = more recent/latest.
        Parses relative times (e.g. '1 hour ago', 'today', '2 days ago')
        or defaults to feed position index.
        """
        if not self.posted_date:
            return float(self.feed_index)

        pd = self.posted_date.lower().strip()

        # Minutes/Hours ago -> 0 to 1
        if "minute" in pd or "dəqiqə" in pd or "минут" in pd:
            return 0.1
        if "hour" in pd or "saat" in pd or "час" in pd:
            # extract hours if possible
            import re
            m = re.search(r'\d+', pd)
            hrs = int(m.group(0)) if m else 1
            return 1.0 + hrs * 0.05
        if "today" in pd or "bu gün" in pd or "сегодня" in pd or "just now" in pd:
            return 1.5
        if "yesterday" in pd or "dünən" in pd or "вчера" in pd or "1 day ago" in pd or "1 gün əvvəl" in pd:
            return 24.0
        if "day" in pd or "gün" in pd or "дн" in pd:
            import re
            m = re.search(r'\d+', pd)
            days = int(m.group(0)) if m else 2
            return days * 24.0

        # Fallback to feed order
        return float(100.0 + self.feed_index)


class BaseCollector(ABC):
    """Abstract collector for gathering raw job source content."""

    @abstractmethod
    def fetch_recent_snippets(self) -> list:
        """Fetches raw web snippets or data from job portals."""
        pass
