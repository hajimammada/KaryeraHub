"""
Proportional Multi-Source Diversity Balancer.
Ensures daily new jobs do not exceed the daily cap (e.g. 15 jobs) and balances
the distribution proportionally across all discovered source portals.
"""
import math
from collections import defaultdict
from typing import List, Dict, Any, TypeVar
from .base import JobItem
from ..utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", JobItem, Dict[str, Any])


class SourceDiversityBalancer:
    """Balances and caps daily vacancies proportionally across multiple job portals."""

    @classmethod
    def balance_and_cap(
        cls,
        jobs: List[T],
        max_total: int = 15
    ) -> List[T]:
        """
        Takes a list of fresh (already deduplicated) vacancies.
        If total jobs <= max_total: returns all jobs (interleaved by source).
        If total jobs > max_total: proportionally selects up to max_total jobs
        using the Largest Remainder (Hare-Niemeyer) method and interleaves them.
        """
        if not jobs:
            return []

        if max_total <= 0:
            return []

        # 1. Group jobs by source portal
        grouped_by_source: Dict[str, List[T]] = defaultdict(list)
        for job in jobs:
            source = getattr(job, "source", None) or (job.get("source") if isinstance(job, dict) else "unknown")
            grouped_by_source[source].append(job)

        total_available = len(jobs)
        logger.info(
            f"⚖️ Balancing {total_available} fresh vacancies across "
            f"{len(grouped_by_source)} sources (Daily Cap: {max_total}). Source counts: " +
            ", ".join(f"{k}: {len(v)}" for k, v in grouped_by_source.items())
        )

        # If total is within cap, sort by freshness and return
        if total_available <= max_total:
            interleaved = cls._interleave_sources(grouped_by_source)
            return sorted(
                interleaved,
                key=lambda j: j.get_sort_key() if hasattr(j, "get_sort_key") else 0
            )

        # 2. Calculate proportional quota using Largest Remainder Method
        quotas: Dict[str, int] = {}
        remainders: List[tuple] = []
        allocated = 0

        for source, source_jobs in grouped_by_source.items():
            count = len(source_jobs)
            exact_quota = (count / total_available) * max_total
            base_quota = math.floor(exact_quota)
            
            # Ensure every source with at least 1 job gets at least 1 allocation if possible
            if base_quota == 0 and count > 0 and len(grouped_by_source) <= max_total:
                base_quota = 1

            # Cap base quota by actual available count for that source
            base_quota = min(base_quota, count)
            
            quotas[source] = base_quota
            allocated += base_quota
            remainder = exact_quota - base_quota
            remainders.append((remainder, source))

        # 3. If allocated exceeds max_total (due to minimum 1 guarantees), trim from largest quotas
        while allocated > max_total:
            # Find source with largest quota > 1
            max_source = max(quotas.keys(), key=lambda s: quotas[s])
            if quotas[max_source] > 1:
                quotas[max_source] -= 1
                allocated -= 1
            else:
                # If all are 1, reduce any
                quotas[max_source] -= 1
                allocated -= 1

        # 4. Distribute remaining slots to sources with highest decimal remainders
        # Sort descending by remainder
        remainders.sort(key=lambda x: x[0], reverse=True)
        rem_idx = 0
        while allocated < max_total and rem_idx < len(remainders):
            source = remainders[rem_idx][1]
            if quotas[source] < len(grouped_by_source[source]):
                quotas[source] += 1
                allocated += 1
            rem_idx = (rem_idx + 1) % len(remainders)
            # Break if all sources hit their maximum available
            if all(quotas[s] >= len(grouped_by_source[s]) for s in grouped_by_source):
                break

        logger.info(
            "📊 Proportional Allocation Quotas: " +
            ", ".join(f"{s}: {quotas[s]}/{len(grouped_by_source[s])}" for s in quotas) +
            f" -> Total Selected: {sum(quotas.values())}"
        )

        # 5. Extract the latest allocated jobs per source (sorted by freshness)
        selected_by_source: Dict[str, List[T]] = {}
        for source, q in quotas.items():
            source_jobs = grouped_by_source[source]
            # Sort by sort_key (freshest / lowest sort score first)
            sorted_source_jobs = sorted(
                source_jobs,
                key=lambda j: j.get_sort_key() if hasattr(j, "get_sort_key") else 0
            )
            selected_by_source[source] = sorted_source_jobs[:q]

        # 6. Interleave the selected jobs so postings alternate nicely
        balanced_jobs = cls._interleave_sources(selected_by_source)

        # 7. Stable sort by freshness (latest first)
        final_sorted_jobs = sorted(
            balanced_jobs[:max_total],
            key=lambda j: j.get_sort_key() if hasattr(j, "get_sort_key") else 0
        )
        return final_sorted_jobs

    @classmethod
    def _interleave_sources(cls, grouped: Dict[str, List[T]]) -> List[T]:
        """
        Interleaves items from multiple sources in a round-robin fashion.
        Example: [SourceA_1, SourceB_1, SourceC_1, SourceA_2, SourceB_2, ...]
        """
        interleaved: List[T] = []
        # Create copies of lists
        queues = {k: list(v) for k, v in grouped.items() if v}
        
        while queues:
            empty_sources = []
            for source, queue in list(queues.items()):
                if queue:
                    interleaved.append(queue.pop(0))
                if not queue:
                    empty_sources.append(source)
            for es in empty_sources:
                del queues[es]

        return interleaved
