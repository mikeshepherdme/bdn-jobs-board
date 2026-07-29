# Maine Politics Jobs Board

A composite jobs board for BDN Maine Politics Insider, pulling from:

- **Maine Executive Branch (Workday)** — automated, refreshes daily on weekdays via GitHub Actions.
- **Nonprofit Maine** — manual only. Their `robots.txt` disallows crawling the `/search/` page and job feeds, so this is never scraped.
- **MEMUN Municipal Career Center** — manual only. Their `robots.txt` explicitly disallows `ClaudeBot` site-wide, so this is never scraped by Claude regardless of what's technically possible.

For the two manual sources, the page always shows a "Browse all openings →" link straight to the source, plus whatever curated postings are in `data/manual.json`.

## One-time setup

1. Create a new GitHub repo (or add this as a subfolder of an existing Pages repo, e.g. `bdn-election-embeds`) and push this folder's contents.
2. In the repo's Settings → Pages, set the source to deploy from the branch this lives on (root, or `/jobs-board` if nested).
3. The page will be live at your Pages URL, e.g. `https://<user>.github.io/<repo>/`. Embed that URL in the newsletter as a link, or in an `<iframe>` if your newsletter platform supports it.
4. No secrets or API keys are needed — the Workday endpoint is a public, unauthenticated JSON API.

## How the automated part works

`scripts/fetch_executive_jobs.py` calls Maine's public Workday job-search API for the Executive branch career site, paginates through every posting, and keeps only titles matching `TITLE_KEYWORDS` (commissioner, director, policy, communications, legislative, counsel, etc.). Results are written to `data/executive.json`, which `index.html` fetches client-side.

`.github/workflows/update-jobs.yml` runs that script on a cron schedule (weekdays, 7am ET) and commits `data/executive.json` if it changed.

**Tuning the filter:** the state board is ~250-350 postings at any time, almost all line-staff roles (transportation workers, caseworkers, nurses, etc.). `TITLE_KEYWORDS` in the script is what narrows that down to politically-relevant roles. If the board is too sparse or too noisy, edit that list — it's a plain Python list of lowercase words/phrases matched with word boundaries against job titles.

## How the manual part works

`data/manual.json` has a `sources` array (Nonprofit Maine, MEMUN) with a `jobs` list and a `lastUpdated` timestamp. To refresh:

1. Ask Claude to open the relevant site in Chrome (as your logged-in browser session — not as an automated crawler) and pull current relevant openings.
2. Claude (or you) updates the matching entry in `data/manual.json` with a job list and sets `lastUpdated` to the current date, then commits.

Job entry shape:

```json
{
  "title": "Communications Director",
  "org": "Example Nonprofit",
  "location": "Portland, Maine",
  "postedOn": "Posted 3 days ago",
  "url": "https://example.org/job/123"
}
```

## Files

- `index.html` — the board itself, static, no build step, no external dependencies.
- `data/executive.json` — auto-generated, do not hand-edit (it'll be overwritten).
- `data/manual.json` — hand-maintained.
- `scripts/fetch_executive_jobs.py` — the Workday fetch/filter script.
- `.github/workflows/update-jobs.yml` — the cron job.
