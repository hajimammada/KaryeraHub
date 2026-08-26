"""
Gemini AI extraction engine for unstructured web job content.
Converts raw HTML snippets and text into validated JobItem instances.
"""
import re
import json
import time
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from .base import JobItem
from ..utils.logger import get_logger

logger = get_logger(__name__)

class GeminiExtractor:
    """Uses Google Gemini API with JSON structured output to extract job vacancies."""

    BASE_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, model_name: str = "gemini-3.1-flash-lite"):
        self.api_key = api_key
        self.model_name = model_name
        self.fallback_models = [
            model_name,
            "gemini-3.1-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-3.1-flash-lite-preview",
            "gemini-3-flash-preview",
            "gemini-3.7-flash"
        ]

    @staticmethod
    def _clean_html_content(raw_content: str) -> str:
        """Strips out styles, scripts, svg, and head boilerplate to expose clean body markup."""
        # 1. Remove style, script, svg, head tags and comments
        cleaned = re.sub(r'<style[^>]*>.*?</style>', '', raw_content, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<script[^>]*>.*?</script>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<svg[^>]*>.*?</svg>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)

        # 2. Extract body if available
        body_match = re.search(r'<body[^>]*>(.*?)</body>', cleaned, re.DOTALL | re.IGNORECASE)
        if body_match:
            cleaned = body_match.group(1)

        # 3. Collapse excessive whitespace
        cleaned = re.sub(r'\n\s*\n+', '\n', cleaned)
        return cleaned.strip()

    # Known global spam/mass-hiring recruiters that clutter Azerbaijan job feeds
    SPAM_COMPANIES = {
        "agoda", "bairesdev", "turing", "crossover", "canonical",
        "testgorilla", "remotasks", "appen", "welocalize", "outlier",
        "dataannotation", "invisible technologies"
    }

    @classmethod
    def is_spam_listing(cls, company: str, jobname: str) -> bool:
        """Filters out mass-hiring spam aggregators or generic scam postings."""
        comp_lower = company.lower().strip()
        job_lower = jobname.lower().strip()

        for spam in cls.SPAM_COMPANIES:
            if spam in comp_lower:
                return True

        if "remote survey" in job_lower or "online rater" in job_lower or "data annotation" in job_lower:
            return True

        return False

    @staticmethod
    def clean_job_url(link: str, base_url: str) -> str:
        """Cleans tracking query parameters and normalizes job URLs."""
        if not link:
            return ""
        
        # For job detail pages (e.g. /jobs/view/..., /vacancies/..., /vakansiya/...), strip tracking query string
        if any(p in link for p in ["/jobs/view/", "/vacancies/", "/vakansiya/", "/vacancy/", "/elan/"]):
            clean_link = link.split('?')[0]
        else:
            clean_link = re.sub(r'(\?|&)(position|pageNum|refId|trackingId|trk|utm_[^&]+|ref|mid)=[^&]*', '', link)
            clean_link = clean_link.rstrip('?&')

        clean_link = clean_link.strip()

        # Prepend base URL if relative
        if not clean_link.startswith("http://") and not clean_link.startswith("https://"):
            clean_link = f"{base_url.rstrip('/')}/{clean_link.lstrip('/')}"

        return clean_link

    def extract_jobs_from_content(
        self,
        raw_content: str,
        portal_name: str,
        base_url: str
    ) -> List[JobItem]:
        """
        Sends preprocessed HTML/text snippet to Gemini and extracts structured job listings.
        """
        if not raw_content or len(raw_content.strip()) < 50:
            logger.warning(f"Empty or too short content received for portal: {portal_name}")
            return []

        # Preprocess and clean HTML to avoid head/style noise
        clean_content = self._clean_html_content(raw_content)
        snippet = clean_content[:30000]

        prompt = f"""You are a specialized vacancy extraction system for Azerbaijani job portals and LinkedIn jobs located in Azerbaijan.
Extract all distinct job vacancies found in the provided HTML/text from {portal_name}.

Portal Details:
- Name: {portal_name}
- Base URL: {base_url}

Requirements:
1. For each job vacancy, extract:
   - "jobname": The job title (in original language).
   - "company": The company/employer name.
   - "link": The absolute direct URL to the vacancy.
   - "posted_date": The date or relative posted time if visible (e.g. "2 hours ago", "today", "yesterday", "2026-08-25").
2. SPAM FILTER (CRITICAL):
   - IGNORE mass-hiring spam aggregators (Agoda, BairesDev, Turing, Crossover, Canonical, survey scams).
   - Only include genuine jobs in or for Azerbaijan.
3. Return ONLY a valid JSON array matching this schema:
[
  {{
    "jobname": "Full Job Title",
    "company": "Company Name",
    "link": "https://...",
    "posted_date": "1 hour ago"
  }}
]
Do not include markdown fences, code blocks, or extra text.

Raw Content:
{snippet}
"""
        raw_json_str = self._call_gemini_with_retries(prompt)
        if not raw_json_str:
            logger.warning(f"No response received from Gemini for {portal_name}")
            return []

        return self._parse_json_to_jobs(raw_json_str, portal_name, base_url)

    def _call_gemini_with_retries(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Calls Gemini API with exponential backoff and fallback model switching."""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }
        payload_bytes = json.dumps(payload).encode("utf-8")

        for attempt in range(1, max_retries + 1):
            model = self.fallback_models[(attempt - 1) % len(self.fallback_models)]
            url = f"{self.BASE_ENDPOINT}/{model}:generateContent?key={self.api_key}"

            req = urllib.request.Request(
                url,
                data=payload_bytes,
                headers={"Content-Type": "application/json"}
            )

            try:
                logger.debug(f"Calling Gemini API (model: {model}, attempt {attempt}/{max_retries})...")
                with urllib.request.urlopen(req, timeout=25) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts and "text" in parts[0]:
                                return parts[0]["text"]
            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8", errors="ignore")
                logger.warning(f"Gemini API HTTP {e.code} on model {model}: {error_body[:200]}")
                time.sleep(2 * attempt)
            except Exception as e:
                logger.warning(f"Gemini API error (attempt {attempt}/{max_retries}): {e}")
                time.sleep(2 * attempt)

        return None

    def _parse_json_to_jobs(self, json_str: str, portal_name: str, base_url: str) -> List[JobItem]:
        """Parses and sanitizes the JSON response into JobItem objects."""
        clean_str = json_str.strip()
        # Handle cases where model might wrap in ```json ... ```
        if clean_str.startswith("```json"):
            clean_str = clean_str[7:]
        elif clean_str.startswith("```"):
            clean_str = clean_str[3:]
        if clean_str.endswith("```"):
            clean_str = clean_str[:-3]
        clean_str = clean_str.strip()

        items = None
        try:
            items = json.loads(clean_str)
        except json.JSONDecodeError:
            # Fallback 1: Use raw_decode to read up to valid JSON end
            try:
                decoder = json.JSONDecoder()
                clean_str_l = clean_str.lstrip()
                if clean_str_l.startswith('['):
                    items, _ = decoder.raw_decode(clean_str_l)
            except Exception:
                pass

            # Fallback 2: Regex extract first valid JSON array
            if items is None:
                array_match = re.search(r'\[\s*\{.*?\}\s*\]', clean_str, re.DOTALL)
                if array_match:
                    try:
                        items = json.loads(array_match.group(0))
                    except Exception:
                        pass

        if items is None:
            logger.error(f"Failed to parse Gemini response as JSON for {portal_name}. Response snippet: {clean_str[:200]}")
            return []

        if not isinstance(items, list):
            if isinstance(items, dict) and "vacancies" in items:
                items = items["vacancies"]
            elif isinstance(items, dict) and "jobs" in items:
                items = items["jobs"]
            else:
                items = [items]

        job_items = []
        for idx, it in enumerate(items):
            if not isinstance(it, dict):
                continue
            jobname = (it.get("jobname") or it.get("title") or it.get("job_title") or "").strip()
            company = (it.get("company") or it.get("company_name") or "Qeyd edilməyib").strip()
            link = (it.get("link") or it.get("url") or "").strip()
            posted_date = (it.get("posted_date") or it.get("date") or "").strip() or None

            if not jobname or not link:
                continue

            # Check and drop spam mass recruiters (e.g. Agoda, Turing, etc.)
            if self.is_spam_listing(company=company, jobname=jobname):
                logger.debug(f"Skipping spam job listing: {jobname} at {company}")
                continue

            # Clean and normalize link
            clean_url = self.clean_job_url(link, base_url)

            job = JobItem(
                jobname=jobname,
                company=company,
                link=clean_url,
                source=portal_name,
                posted_date=posted_date,
                feed_index=idx
            )
            if job.is_valid():
                job_items.append(job)

        logger.info(f"Successfully parsed {len(job_items)} validated jobs from {portal_name}")
        return job_items
