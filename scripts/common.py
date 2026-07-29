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
