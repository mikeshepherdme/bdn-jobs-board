#!/usr/bin/env python3
"""
Fetches Maine Executive Branch job postings from the state's public Workday
job-search API and filters them down to roles relevant to a political
newsletter audience. Writes data/executive.json.

Source: https://maine.wd5.myworkdayjobs.com/Executive
robots.txt for this host explicitly allows crawling /Executive/ (only
/refreshFacet/ is disallowed), so hitting this JSON API on a schedule is fine.
"""
import json
import re
import urllib.request
from datetime import datetime, timezone

API_URL = "https://maine.wd5.myworkdayjobs.com/wday/cxs/maine/Executive/jobs"
JOB_BASE_URL = "https://maine.wd5.myworkdayjobs.com/Executive"
PAGE_SIZE = 20  # Workday's API rejects anything larger with HTTP 400
OUTPUT_PATH = "data/executive.json"

# Titles containing any of these (case-insensitive) are treated as relevant
# to Maine political/government coverage. Tune this list as the board proves
# too noisy or too sparse.
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


def fetch_all_postings():
    # Workday's "total" field is only reliable on the first (offset=0) request;
    # on later pages it has been observed to drop to 0 even though jobPostings
    # keeps returning real, distinct results. So capture total once up front
    # and paginate against that fixed count instead of trusting every response.
    postings = []
    offset = 0
    total = None
    while total is None or offset < total:
        body = json.dumps(
            {"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": ""}
        ).encode("utf-8")
        req = urllib.request.Request(
            API_URL, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
        if total is None:
            total = payload["total"]
        postings.extend(payload["jobPostings"])
        offset += PAGE_SIZE
    return postings


TITLE_KEYWORD_PATTERNS = [
    re.compile(r"\b" + re.escape(keyword) + r"\b") for keyword in TITLE_KEYWORDS
]


def is_relevant(title):
    lowered = title.lower()
    return any(pattern.search(lowered) for pattern in TITLE_KEYWORD_PATTERNS)


def main():
    postings = fetch_all_postings()
    relevant = [p for p in postings if is_relevant(p["title"])]

    jobs = [
        {
            "title": p["title"],
            "location": p.get("locationsText", ""),
            "postedOn": p.get("postedOn", ""),
            "url": JOB_BASE_URL + p["externalPath"],
        }
        for p in relevant
    ]

    output = {
        "source": "Maine Executive Branch (Workday)",
        "sourceSearchUrl": JOB_BASE_URL,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "totalPostings": len(postings),
        "matchedPostings": len(jobs),
        "jobs": jobs,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    print(f"Fetched {len(postings)} total postings, {len(jobs)} matched filter.")


if __name__ == "__main__":
    main()
