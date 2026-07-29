"""Shared fetch logic for Maine's Workday-hosted job boards (Executive,
Judicial). Both are the same underlying Workday CxS API, differing only by
site name.
"""
import json
import urllib.request

PAGE_SIZE = 20  # Workday's API rejects anything larger with HTTP 400
ARCHIVE_PATH = "data/archive.json"


def fetch_all_postings(site):
    api_url = f"https://maine.wd5.myworkdayjobs.com/wday/cxs/maine/{site}/jobs"
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
            api_url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
        if total is None:
            total = payload["total"]
        postings.extend(payload["jobPostings"])
        offset += PAGE_SIZE

    # Workday occasionally returns malformed entries with just a bulletFields
    # req number and no title/externalPath (seen in the wild, cause unclear).
    # Skip those rather than crashing.
    return [p for p in postings if p.get("title") and p.get("externalPath")]


def fetch_job_detail(site, external_path):
    """Fetch hiring department + real posted/closing dates for one posting.
    Only called for already-filtered matches (a handful per run), so the
    extra request per job is cheap. Returns Nones on any failure so a single
    bad detail fetch can't take down the whole run.
    """
    detail_api_url = f"https://maine.wd5.myworkdayjobs.com/wday/cxs/maine/{site}"
    try:
        req = urllib.request.Request(detail_api_url + external_path)
        with urllib.request.urlopen(req, timeout=30) as resp:
            detail = json.load(resp)
        org = detail.get("hiringOrganization", {}).get("name", "")
        info = detail.get("jobPostingInfo", {})
        return org, info.get("startDate"), info.get("endDate")
    except Exception:
        return "", None, None
