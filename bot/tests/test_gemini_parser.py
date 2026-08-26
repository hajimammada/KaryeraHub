"""
Unit tests for GeminiExtractor JSON response parsing and sanitization.
"""
import pytest
from src.scraper.gemini_extractor import GeminiExtractor

@pytest.fixture
def extractor():
    return GeminiExtractor(api_key="mock_key", model_name="gemini-flash-latest")


def test_parse_clean_json(extractor: GeminiExtractor):
    raw_json = """
    [
        {"jobname": "Frontend Developer", "company": "CodeAZ", "link": "https://boss.az/vacancies/frontend-dev"},
        {"jobname": "Qrafik Dizayner", "company": "Creative Baku", "link": "https://boss.az/vacancies/designer"}
    ]
    """
    jobs = extractor._parse_json_to_jobs(raw_json, portal_name="boss.az", base_url="https://boss.az")
    assert len(jobs) == 2
    assert jobs[0].jobname == "Frontend Developer"
    assert jobs[0].company == "CodeAZ"
    assert jobs[0].link == "https://boss.az/vacancies/frontend-dev"
    assert jobs[0].source == "boss.az"


def test_parse_wrapped_markdown_json(extractor: GeminiExtractor):
    raw_json = """```json
    [
        {"jobname": "Python Engineer", "company": "Baku AI", "link": "/vacancies/ai-engineer"}
    ]
    ```"""
    jobs = extractor._parse_json_to_jobs(raw_json, portal_name="jobsearch.az", base_url="https://jobsearch.az")
    assert len(jobs) == 1
    assert jobs[0].jobname == "Python Engineer"
    # Verify relative link was converted to absolute URL
    assert jobs[0].link == "https://jobsearch.az/vacancies/ai-engineer"


def test_parse_invalid_or_missing_fields(extractor: GeminiExtractor):
    raw_json = """
    [
        {"jobname": "Valid Job", "company": "Valid Corp", "link": "https://boss.az/1"},
        {"jobname": "", "company": "No Title", "link": "https://boss.az/2"},
        {"company": "No Jobname", "link": "https://boss.az/3"},
        {"jobname": "No Link", "company": "Some Corp", "link": ""}
    ]
    """
    jobs = extractor._parse_json_to_jobs(raw_json, portal_name="boss.az", base_url="https://boss.az")
    assert len(jobs) == 1
    assert jobs[0].jobname == "Valid Job"


def test_parse_and_filter_spam_companies(extractor: GeminiExtractor):
    raw_json = """
    [
        {"jobname": "Genuine Engineer", "company": "Hilton Baku", "link": "https://az.linkedin.com/jobs/view/100"},
        {"jobname": "Software Engineer", "company": "Agoda", "link": "https://az.linkedin.com/jobs/view/200"},
        {"jobname": "Remote Developer", "company": "BairesDev", "link": "https://az.linkedin.com/jobs/view/300"},
        {"jobname": "AI Specialist", "company": "Turing", "link": "https://az.linkedin.com/jobs/view/400"},
        {"jobname": "C++ Engineer", "company": "Canonical", "link": "https://az.linkedin.com/jobs/view/500"}
    ]
    """
    jobs = extractor._parse_json_to_jobs(raw_json, portal_name="linkedin", base_url="https://az.linkedin.com")
    assert len(jobs) == 1
    assert jobs[0].company == "Hilton Baku"


def test_clean_linkedin_urls(extractor: GeminiExtractor):
    raw_json = """
    [
        {
            "jobname": "Front Desk Agent",
            "company": "Marriott",
            "link": "https://az.linkedin.com/jobs/view/12345?position=1&pageNum=0&refId=abc1234&trackingId=xyz5678",
            "posted_date": "2 hours ago"
        }
    ]
    """
    jobs = extractor._parse_json_to_jobs(raw_json, portal_name="linkedin", base_url="https://az.linkedin.com")
    assert len(jobs) == 1
    # Tracking parameters must be stripped
    assert jobs[0].link == "https://az.linkedin.com/jobs/view/12345"
    assert jobs[0].posted_date == "2 hours ago"
