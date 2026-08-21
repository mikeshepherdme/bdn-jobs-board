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

from common import archive_removed, is_relevant, load_json, now_iso, today_iso
from workday_common import ARCHIVE_PATH, fetch_all_postings, fetch_job_detail

SITE = "Executive"
JOB_BASE_URL = "https://maine.wd5.myworkdayjobs.com/Executive"
OUTPUT_PATH = "data/executive.json"
SOURCE_NAME = "Maine Executive Branch (Workday)"


def main():
    today = today_iso()

    previous = load_json(OUTPUT_PATH, None)
    previous_jobs_by_url = {j["url"]: j for j in previous["jobs"]} if previous else {}

    postings = fetch_all_postings(SITE)
    relevant = [p for p in postings if is_relevant(p["title"])]

    jobs = []
    for p in relevant:
        url = JOB_BASE_URL + p["externalPath"]
        firstSeenOn = previous_jobs_by_url.get(url, {}).get("firstSeenOn", today)
        org, postedDate, closingDate, salary = fetch_job_detail(SITE, p["externalPath"])
        jobs.append(
            {
                "title": p["title"],
                "org": org,
                "location": p.get("locationsText", ""),
                "salary": salary,
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
        "sourceSearchUrl": JOB_BASE_URL,
        "generatedAt": now_iso(),
        "totalPostings": len(postings),
        "matchedPostings": len(jobs),
        "jobs": jobs,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    print(
        f"Fetched {len(postings)} total postings, {len(jobs)} matched filter, "
        f"{len(removed)} archived as removed."
    )


if __name__ == "__main__":
    main()
