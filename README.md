# MPI Jobs Board

A composite jobs board for Maine Politics Insider, pulling from:

- **Maine Executive Branch (Workday)** — automated.
- **Maine Judicial Branch (Workday)** — automated.
- **Maine Legislature (Taleo)** — automated.
- **Nonprofit Maine** — manual only. Their `robots.txt` disallows crawling the `/search/` page and job feeds, so this is never scraped.
- **MEMUN Municipal Career Center** — manual only. Their `robots.txt` explicitly disallows `ClaudeBot` site-wide, so this is never scraped by Claude regardless of what's technically possible.

All sources merge into one flat, searchable, sortable list in `index.html` — no per-source columns. For the two manual sources, jobs come from whatever's curated in `data/manual.json`; a "Browse full listings" link in the footer covers everything else.

## One-time setup

1. Create a new GitHub repo (or add this as a subfolder of an existing Pages repo, e.g. `bdn-election-embeds`) and push this folder's contents.
2. In the repo's Settings → Pages, set the source to deploy from the branch this lives on (root, or `/jobs-board` if nested).
3. The page will be live at your Pages URL, e.g. `https://<user>.github.io/<repo>/`. Embed that URL in the newsletter as a link, or in an `<iframe>` if your newsletter platform supports it.
4. No secrets or API keys are needed — all three automated sources are public, unauthenticated endpoints.

## How the automated part works

Three scripts, one shared filter:

- `scripts/fetch_executive_jobs.py` and `scripts/fetch_judicial_jobs.py` call Maine's public Workday job-search API for the Executive and Judicial branch career sites respectively (both share fetch/detail logic in `scripts/workday_common.py`). For each match, a second request to the job's detail endpoint pulls the real hiring department and actual posted/closing dates (`hiringOrganization.name`, `startDate`, `endDate`) rather than relying on vague relative text like "Posted 7 Days Ago."
- `scripts/fetch_legislature_jobs.py` fetches the Legislature's Taleo career site. Listings render directly in server-rendered HTML (no JS execution needed), and each posting's detail page embeds a schema.org `JobPosting` JSON-LD block with the same kind of real date/org data.
- All three filter titles through the same `is_relevant()` / `TITLE_KEYWORDS` list in `scripts/common.py` (commissioner, director, policy, communications, legislative, counsel, etc.), so filtering behaves consistently across sources.
- Results write to `data/executive.json`, `data/judicial.json`, and `data/legislature.json` respectively, which `index.html` fetches client-side and merges into one list.

`.github/workflows/update-jobs.yml` runs all three scripts on a cron schedule (weekdays, 7am ET, DST-proof — see the "Check if it's actually 7am Eastern" step) and commits whichever data files changed.

**Tuning the filter:** the Executive board alone is ~250-350 postings at any time, almost all line-staff roles (transportation workers, caseworkers, nurses, etc.); Judicial is dominated by clerks and marshals. `TITLE_KEYWORDS` in `scripts/common.py` is what narrows that down to politically-relevant roles, shared across every automated source. If a board is too sparse or too noisy, edit that one list — it's a plain Python list of lowercase words/phrases matched with word boundaries against job titles.

## Archiving removed postings

Each fetch script diffs against its own previous run (by URL) before overwriting its data file. Anything that disappears — filled, pulled, or expired — gets logged to `data/archive.json` (title, org, location, first-seen date, removed date, link) instead of vanishing silently. This is a **private log, not shown on the public board** — it's there for your own research (e.g. following up on who got hired after a commissioner-level posting closed).

## How the manual part works

`data/manual.json` has a `sources` array (Nonprofit Maine, MEMUN) with a `jobs` list and a `lastUpdated` timestamp. To refresh:

1. Ask Claude to open the relevant site in Chrome (as your logged-in browser session — not as an automated crawler) and pull current relevant openings.
2. Claude (or you) updates the matching entry in `data/manual.json` with a job list and sets `lastUpdated` to the current date, then commits. If a previously-listed job is now gone, move it into `data/archive.json` the same way the automated scripts do, rather than just deleting it.

Job entry shape (same schema as the automated sources):

```json
{
  "title": "Communications Director",
  "org": "Example Nonprofit",
  "location": "Portland, Maine",
  "postedDate": "2026-07-20",
  "closingDate": null,
  "url": "https://example.org/job/123",
  "firstSeenOn": "2026-07-29"
}
```

## Board features

- **Search** — filters live across title, org, location, and source.
- **Sort** — newest posted (default), closing soonest, source, title A–Z, location A–Z.
- **"New" badge** — shown when `postedDate` is within the last 3 days (the actual posting date, not when we started tracking it).
- **"Closes in N days" badge** — shown when `closingDate` is within the next 7 days.
- **CTA card** — drives readers back to the Maine Politics Insider newsletter signup. Update the placeholder link in `index.html` (`#ctaLink`) with the real subscribe URL.

## Files

- `index.html` — the board itself: flat list, search, sort, badges. Static, no build step, no external dependencies.
- `data/executive.json`, `data/judicial.json`, `data/legislature.json` — auto-generated, do not hand-edit (they'll be overwritten).
- `data/manual.json` — hand-maintained.
- `data/archive.json` — auto-maintained private log of removed postings across all sources.
- `scripts/common.py` — shared keyword filter, JSON helpers, and archive logic.
- `scripts/workday_common.py` — shared Workday fetch/detail logic (used by Executive + Judicial).
- `scripts/fetch_executive_jobs.py`, `scripts/fetch_judicial_jobs.py`, `scripts/fetch_legislature_jobs.py` — per-source fetch/filter scripts.
- `.github/workflows/update-jobs.yml` — the cron job.
