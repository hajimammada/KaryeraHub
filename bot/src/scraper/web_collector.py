"""
Multi-source Web Collector for Azerbaijani Job Portals.
Fetches fresh listing pages with browser-like headers and error resilience.
"""
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from ..utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class JobPortalSource:
    name: str
    url: str
    base_url: str
    enabled: bool = True


class WebCollector:
    """Fetches raw web content from Azerbaijani job portals."""

    DEFAULT_SOURCES = [
        JobPortalSource(
            name="jobsearch.az",
            url="https://jobsearch.az/vacancies",
            base_url="https://jobsearch.az"
        ),
        JobPortalSource(
            name="hellojob.az",
            url="https://hellojob.az/vakansiyalar",
            base_url="https://hellojob.az"
        ),
        JobPortalSource(
            name="linkedin",
            url="https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?location=Azerbaijan&f_TPR=r604800",
            base_url="https://az.linkedin.com"
        ),
        JobPortalSource(
            name="ishelanlari.az",
            url="https://ishelanlari.az",
            base_url="https://ishelanlari.az"
        ),
        JobPortalSource(
            name="banker.az",
            url="https://banker.az/category/vakansiyalar/",
            base_url="https://banker.az"
        ),
        JobPortalSource(
            name="boss.az",
            url="https://boss.az/vacancies",
            base_url="https://boss.az"
        )
    ]

    def __init__(self, sources: Optional[List[JobPortalSource]] = None):
        self.sources = sources or self.DEFAULT_SOURCES

    def fetch_portal_content(self, source: JobPortalSource) -> Optional[str]:
        """Fetches the raw HTML/text from a single job portal."""
        logger.info(f"Fetching fresh listings from {source.name} ({source.url})...")
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "az,en-US,en;q=0.9,ru;q=0.8",
        }

        req = urllib.request.Request(source.url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                if response.status == 200:
                    raw_html = response.read().decode("utf-8", errors="ignore")
                    logger.debug(f"Successfully fetched {len(raw_html)} bytes from {source.name}")
                    return raw_html
                else:
                    logger.warning(f"{source.name} returned status code {response.status}")
        except urllib.error.HTTPError as e:
            logger.warning(f"HTTP error fetching {source.name}: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            logger.warning(f"Network / URL error fetching {source.name}: {e.reason}")
        except Exception as e:
            logger.warning(f"Unexpected error fetching {source.name}: {e}")

        return None

    def fetch_all_sources(self) -> List[Dict[str, Any]]:
        """
        Fetches all enabled portal sources and returns a list of dictionaries:
        [{'portal': source, 'content': html_content}]
        """
        results = []
        for src in self.sources:
            if not src.enabled:
                continue
            content = self.fetch_portal_content(src)
            if content:
                results.append({
                    "portal": src,
                    "content": content
                })
        return results
