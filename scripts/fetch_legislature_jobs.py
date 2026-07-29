#!/usr/bin/env python3
"""
Fetches Maine Legislature job postings from its public Taleo career site and
filters them down to roles relevant to a political newsletter audience.
Writes data/legislature.json.

Source: https://phf.tbe.taleo.net/phf01/ats/careers/v2/searchResults?org=MAINELEGIS&cws=38
This Taleo instance has no real robots.txt (the path returns Oracle's generic
"come back soon" error page, not a disallow list), so no crawl restriction is
declared. Listings render directly in the server-rendered HTML (confirmed via
curl, no JS execution needed); each posting's detail page also embeds a
schema.org JobPosting JSON-LD block with the real posted/closing dates.
"""
import json
import re
import urllib.request

from common import archive_removed, is_relevant, load_json, now_iso, today_iso
from workday_common import ARCHIVE_PATH

SEARCH_URL = "https://phf.tbe.taleo.net/phf01/ats/careers/v2/searchResults?org=MAINELEGIS&cws=38"
DETAIL_URL = "https://phf.tbe.taleo.net/phf01/ats/careers/v2/viewRequisition?org=MAINELEGIS&cws=38&rid={rid}"
OUTPUT_PATH = "data/legislature.json"
SOURCE_NAME = "Maine Legislature (Taleo)"

LISTING_PATTERN = re.compile(
    r'<h4 class="oracletaleocwsv2-head-title"><a href="[^"]*[?&]rid=(\d+)"[^>]*>([^<]+)</a></h4>'
    r'\s*<div tabindex="0" >([^<]*)</div>',
    re.DOTALL,
)
JSONLD_PATTERN = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read().decode("utf-8")


def fetch_listings():
    html = fetch(SEARCH_URL)
    return [
        {"rid": rid, "title": title.strip(), "department": dept.strip()}
        for rid, title, dept in LISTING_PATTERN.findall(html)
    ]


def fetch_detail(rid):
    try:
        html = fetch(DETAIL_URL.format(rid=rid))
        m = JSONLD_PATTERN.search(html)
        d = json.loads(m.group(1))
        org = d.get("hiringOrganization", {}).get("name", "")
        location = d.get("jobLocation", {}).get("address", {}).get("addressLocality", "")
        postedDate = (d.get("datePosted") or "")[:10] or None
        closingDate = (d.get("validThrough") or "")[:10] or None
        return org, location, postedDate, closingDate
    except Exception:
        return "", "", None, None


def main():
    today = today_iso()

    previous = load_json(OUTPUT_PATH, None)
    previous_jobs_by_url = {j["url"]: j for j in previous["jobs"]} if previous else {}

    listings = fetch_listings()
    relevant = [p for p in listings if is_relevant(p["title"])]

    jobs = []
    for p in relevant:
        url = DETAIL_URL.format(rid=p["rid"])
        firstSeenOn = previous_jobs_by_url.get(url, {}).get("firstSeenOn", today)
        org, location, postedDate, closingDate = fetch_detail(p["rid"])
        jobs.append(
            {
                "title": p["title"],
                "org": org or p["department"],
                "location": location,
                "postedDate": postedDate or firstSeenOn,
                "closingDate": closingDate,
                "url": url,
                "firstSeenOn": firstSeenOn,
            }
        )

    current_urls = {j["url"] for j in jobs}
    removed = archive_removed(previous_jobs_by_url, current_urls, SOURCE_NAME, ARCHIVE_PATH)

    output = {
        "source": SOURCE_NAME,
        "sourceSearchUrl": SEARCH_URL,
        "generatedAt": now_iso(),
        "totalPostings": len(listings),
        "matchedPostings": len(jobs),
        "jobs": jobs,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    print(
        f"Fetched {len(listings)} total postings, {len(jobs)} matched filter, "
        f"{len(removed)} archived as removed."
    )


if __name__ == "__main__":
    main()
