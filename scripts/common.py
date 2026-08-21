"""Shared helpers used by all fetch_*.py scripts: relevance filtering,
JSON I/O, and the "diff against last run, archive what disappeared" logic.
"""
import json
import re
from datetime import datetime, timezone

# Titles containing any of these (case-insensitive, word-boundary matched) are
# treated as relevant to Maine political/government coverage. Shared across
# all sources so filtering behaves consistently; tune as it proves too noisy
# or too sparse for a given source.
TITLE_KEYWORDS = [
    "commissioner",
    "deputy commissioner",
    "director",
    "deputy director",
    "chief of staff",
    "chief legal",
    "general counsel",
    "counsel",
    "policy",
    "communications",
    "public information",
    "legislative",
    "executive director",
    "secretary of state",
    "state auditor",
    "press secretary",
    "advisor",
    "adviser",
    "ombudsman",
]

TITLE_KEYWORD_PATTERNS = [
    re.compile(r"\b" + re.escape(keyword) + r"\b") for keyword in TITLE_KEYWORDS
]


def is_relevant(title):
    lowered = title.lower()
    return any(pattern.search(lowered) for pattern in TITLE_KEYWORD_PATTERNS)


# Matches a dollar-amount range like "$74,713.60 - $105,809.60/Annually" or
# "$22.63 - $32.54/Hour". Salary is never a structured field in any of these
# sources (Workday, Taleo) -- it's embedded in free-text HTML descriptions --
# so this is a best-effort extraction, not guaranteed to match every posting.
SALARY_RANGE_PATTERN = re.compile(
    r"\$[\d,]+(?:\.\d{2})?\s*(?:-|to|–)\s*\$[\d,]+(?:\.\d{2})?"
    r"(?:\s*/\s*\w+|\s*per\s*\w+|\s*annually|\s*hourly)?",
    re.IGNORECASE,
)

# Fallback for a single flat figure rather than a range, e.g. "Salary: $24.64
# Per Hour". Anchored to the word "salary" immediately followed by a dollar
# amount (optionally through a colon), so it doesn't pick up unrelated dollar
# figures elsewhere in a description (benefit values, budget numbers, etc).
SALARY_SINGLE_PATTERN = re.compile(
    r"salary\s*:?\s*(\$[\d,]+(?:\.\d{2})?(?:\s*/\s*\w+|\s*per\s*\w+|\s*annually|\s*hourly)?)",
    re.IGNORECASE,
)


def extract_salary(html_description):
    """Best-effort salary extraction from a free-text job description (may
    contain HTML tags). Tries a range first, then a single flat figure.
    Returns '' if neither pattern is found.
    """
    if not html_description:
        return ""
    text = re.sub(r"<[^>]+>", " ", html_description)
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text)
    m = SALARY_RANGE_PATTERN.search(text)
    if m:
        return m.group(0).strip()
    m = SALARY_SINGLE_PATTERN.search(text)
    return m.group(1).strip() if m else ""


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def today_iso():
    return datetime.now(timezone.utc).date().isoformat()


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def archive_removed(previous_jobs_by_url, current_urls, source_name, archive_path):
    """Move jobs present last run but missing this run into the shared
    archive log, rather than letting them silently disappear."""
    removed = [j for j in previous_jobs_by_url.values() if j["url"] not in current_urls]
    if removed:
        today = today_iso()
        archive = load_json(archive_path, {"archived": []})
        for j in removed:
            archive["archived"].append(
                {
                    "source": source_name,
                    "title": j["title"],
                    "org": j.get("org", ""),
                    "location": j.get("location", ""),
                    "url": j["url"],
                    "firstSeenOn": j.get("firstSeenOn"),
                    "removedOn": today,
                }
            )
        with open(archive_path, "w") as f:
            json.dump(archive, f, indent=2)
            f.write("\n")
    return removed
