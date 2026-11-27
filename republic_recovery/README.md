# Rook Republic Recovery

Backend scaffold for rebuilding the Rook Republic Chess.com sidebar while
preserving its original sections, content, links, and blue/cyan visual identity.

## Current stage

This starter contains:
- `config.json` — club identity, theme, dimensions, API settings, and paths.
- `data/*.json` — editable structured sidebar content seeded from the supplied
  after-crash HTML.
- `data/events.txt` — event database placeholder using the established format.
- `generator/api.py` — Chess.com PubAPI client with serial requests, a 12-hour
  minimum cache, ETag/Last-Modified support, retries, and stale-cache fallback.

The renderer exports separate PNG sections for the census, newest citizens,
achievements, Hall of Heroes, partner clubs, and Quick Links. HTML companions and
the GitHub Actions workflow will be added in later stages.

## Setup

```bash
python -m pip install -r requirements.txt
python -m generator.api
python -m generator.build
```

Run commands from this directory. `python -m generator.api` prints and caches an API snapshot.
`python -m generator.build` refreshes the snapshot and renders PNGs into `images/`.
The first build needs network access to Chess.com; avatar downloads are optional and cached locally.

## API notes

- Club member count comes from the club profile's `members_count` field.
- Newest citizens are derived by merging `weekly`, `monthly`, and `all_time`,
  de-duplicating usernames, and sorting by their `joined` Unix timestamps.
- Active matches count both `registered` and `in_progress` matches, matching
  the original sidebar's calculation.
- Newest-citizen profile and stats lookups are serial and limited to the
  configured top N.
- Chess.com says PubAPI endpoint data refreshes at most once every 12 hours.
  The client therefore enforces a minimum 12-hour local cache interval.
- If a refresh fails and a cached response exists, the client can use stale
  data and add a warning instead of breaking the whole build.

## Important data review items

- `partners.json` preserves the partner name and URL from the HTML, but flags
  their mismatch for review.
- `quick_links.json` preserves source URLs and flags malformed-looking
  addresses rather than guessing corrections.
- `heroes.json` imports the ROOOK records and their displayed labels from the
  supplied HTML, including source numbering irregularities.
- The achievement completion states are copied from the supplied HTML and
  should be checked against the current club status before launch.

## Attribution

This is an independent community project and is not affiliated with Chess.com.
