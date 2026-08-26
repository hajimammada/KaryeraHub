"""
Unit tests for SourceDiversityBalancer (15 daily cap and proportional multi-source allocation).
"""
import pytest
from src.scraper.base import JobItem
from src.scraper.balancer import SourceDiversityBalancer


def test_balance_when_total_under_cap():
    jobs = [
        JobItem(jobname="Job 1", company="Corp A", link="https://a.az/1", source="jobsearch.az"),
        JobItem(jobname="Job 2", company="Corp B", link="https://b.az/2", source="hellojob.az"),
        JobItem(jobname="Job 3", company="Corp C", link="https://c.az/3", source="ishelanlari.az"),
    ]

    balanced = SourceDiversityBalancer.balance_and_cap(jobs, max_total=15)
    assert len(balanced) == 3


def test_balance_proportional_multi_source_cap_15():
    # 40 from jobsearch.az (40%), 35 from hellojob.az (35%), 25 from ishelanlari.az (25%) -> Total 100
    jobs = []
    for i in range(40):
        jobs.append(JobItem(jobname=f"JS Job {i}", company=f"Corp {i}", link=f"https://js.az/{i}", source="jobsearch.az"))
    for i in range(35):
        jobs.append(JobItem(jobname=f"HJ Job {i}", company=f"Corp {i}", link=f"https://hj.az/{i}", source="hellojob.az"))
    for i in range(25):
        jobs.append(JobItem(jobname=f"IS Job {i}", company=f"Corp {i}", link=f"https://is.az/{i}", source="ishelanlari.az"))

    balanced = SourceDiversityBalancer.balance_and_cap(jobs, max_total=15)
    
    assert len(balanced) == 15

    # Count by source in final selection
    counts = {}
    for j in balanced:
        counts[j.source] = counts.get(j.source, 0) + 1

    # Expected: 40% of 15 = 6, 35% of 15 = 5.25 -> 5, 25% of 15 = 3.75 -> 4
    assert counts["jobsearch.az"] == 6
    assert counts["hellojob.az"] == 5
    assert counts["ishelanlari.az"] == 4


def test_single_source_handling():
    # 30 jobs from a single source
    jobs = [
        JobItem(jobname=f"Job {i}", company=f"Corp {i}", link=f"https://js.az/{i}", source="jobsearch.az")
        for i in range(30)
    ]

    balanced = SourceDiversityBalancer.balance_and_cap(jobs, max_total=15)
    assert len(balanced) == 15
    assert all(j.source == "jobsearch.az" for j in balanced)


def test_source_interleaving():
    jobs = [
        JobItem(jobname="JS 1", company="Corp", link="https://js.az/1", source="jobsearch.az"),
        JobItem(jobname="JS 2", company="Corp", link="https://js.az/2", source="jobsearch.az"),
        JobItem(jobname="HJ 1", company="Corp", link="https://hj.az/1", source="hellojob.az"),
        JobItem(jobname="HJ 2", company="Corp", link="https://hj.az/2", source="hellojob.az"),
    ]

    balanced = SourceDiversityBalancer.balance_and_cap(jobs, max_total=15)
    assert len(balanced) == 4
    
    # Check that sources alternate: JS -> HJ -> JS -> HJ
    sources = [j.source for j in balanced]
    assert sources[0] != sources[1]
    assert sources[1] != sources[2]


def test_empty_jobs():
    balanced = SourceDiversityBalancer.balance_and_cap([], max_total=15)
    assert balanced == []


def test_date_sorting_latest_first():
    jobs = [
        JobItem(jobname="Old Job", company="Corp 1", link="https://a.az/1", source="jobsearch.az", posted_date="3 days ago"),
        JobItem(jobname="Brand New Job", company="Corp 2", link="https://b.az/2", source="hellojob.az", posted_date="1 hour ago"),
        JobItem(jobname="Yesterday Job", company="Corp 3", link="https://c.az/3", source="linkedin", posted_date="yesterday"),
    ]

    balanced = SourceDiversityBalancer.balance_and_cap(jobs, max_total=15)
    assert len(balanced) == 3
    assert balanced[0].jobname == "Brand New Job"
    assert balanced[1].jobname == "Yesterday Job"
    assert balanced[2].jobname == "Old Job"
