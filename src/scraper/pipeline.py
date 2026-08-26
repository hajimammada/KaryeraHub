"""
Complete Job Discovery Pipeline.
Coordinates web collection and Gemini AI extraction.
"""
from typing import List, Optional
from .base import JobItem
from .web_collector import WebCollector
from .gemini_extractor import GeminiExtractor
from ..utils.logger import get_logger

logger = get_logger(__name__)

class JobDiscoveryPipeline:
    """Orchestrates multi-source fetching and Gemini structured extraction."""

    def __init__(
        self,
        gemini_extractor: GeminiExtractor,
        web_collector: Optional[WebCollector] = None
    ):
        self.extractor = gemini_extractor
        self.collector = web_collector or WebCollector()

    def discover_latest_jobs(self) -> List[JobItem]:
        """
        Runs the full discovery cycle across all enabled portals.
        Returns a deduplicated list of valid JobItem instances discovered in this cycle.
        """
        logger.info("🚀 Starting job discovery across Azerbaijani portals...")
        raw_sources = self.collector.fetch_all_sources()
        if not raw_sources:
            logger.warning("No web content could be fetched from portals.")
            return []

        all_jobs: List[JobItem] = []
        for item in raw_sources:
            portal = item["portal"]
            content = item["content"]

            extracted = self.extractor.extract_jobs_from_content(
                raw_content=content,
                portal_name=portal.name,
                base_url=portal.base_url
            )
            all_jobs.extend(extracted)

        # Basic within-cycle deduplication by link
        unique_jobs: List[JobItem] = []
        seen_links = set()
        for j in all_jobs:
            if j.link not in seen_links:
                unique_jobs.append(j)
                seen_links.add(j.link)

        logger.info(f"✨ Job discovery finished: Total {len(unique_jobs)} unique listings extracted from {len(raw_sources)} portals.")
        return unique_jobs
