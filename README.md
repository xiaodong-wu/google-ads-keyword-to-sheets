# Google Ads Keyword Ideas to Google Sheets

A Codex skill that collects keyword ideas from the signed-in Google Ads Keyword Planner in Chrome and keeps wholesale, bulk-purchase, and customization intent. When a domain is supplied it appends unique keywords to the matching tab in the configured **Automatically publish articles** Google Sheet; without a domain it exports a local filtered CSV containing each retained keyword and all of its Google Ads metrics.

The workflow uses the visible Google Ads interface and a one-time CSV export. It does not use the Google Ads API or generate keyword suggestions from another source.

The supplied domain is a destination-tab selector only. The skill never enters it, or a URL derived from it, into the Google Ads website filter. A missing domain is never replaced with a default domain.

## What it does

- Accepts one seed keyword, an optional language, optional location, optional destination-tab domain, and an optional `dry-run` flag.
- Defaults language to English and location to All locations; configures Keyword Planner for the selected language and location, Google Search, and the past 12 months, with no website/site filter.
- Downloads all keyword ideas as CSV and preserves Google Ads relevance order.
- Normalizes text with NFKC and whole-token phrase matching, then removes blocked low-intent phrases and confirmed brands.
- Keeps only ideas containing a wholesale, bulk-purchase, B2B, or customization marker, and removes the seed, duplicates, and keywords already present in the destination tab.
- With a domain, appends at most 500 rows per batch and verifies every written range.
- Copies the latest complete C–E template row inside Google Sheets, writes the keyword and location to A–B, and leaves F–H blank.
- Without a domain, writes a UTF-8 CSV containing the original Google Ads metadata, complete header, and full metric row for every retained keyword, including search volume, competition, and bid ranges.
- Keeps the publishing key inside Google Sheets and out of local files, logs, commands, and reports.

## Requirements

- Codex Desktop with access to the Chrome integration.
- For Sheets mode, access to the Google Drive and Google Sheets integrations.
- A Chrome session signed in to an account that can use Google Ads Keyword Planner and export keyword ideas.
- For Sheets mode, access to the configured Google Sheet and an existing tab whose name exactly matches the normalized domain.
- Python 3.9 or later for the CSV preparation helper and tests.

## Installation

Clone the repository into the Codex skills directory:

```bash
git clone https://github.com/xiaodong-wu/google-ads-keyword-to-sheets.git ~/.codex/skills/google-ads-keyword-to-sheets
```

Restart Codex if the skill is not discovered immediately.

## Usage

Run a read-only dry run first:

```text
$google-ads-keyword-to-sheets keyword="protein powder" language="English" location="United States" domain="www.nutricdmo.com" dry-run
```

Run the live workflow after reviewing the planned destination range:

```text
$google-ads-keyword-to-sheets keyword="protein powder" language="English" location="United States" domain="www.nutricdmo.com"
```

Export a detailed local CSV instead of using Google Sheets by omitting the domain:

```text
$google-ads-keyword-to-sheets keyword="watch" language="English" location="All locations"
```

Language defaults to `English` and location defaults to `All locations`. The domain has no default: providing one selects Sheets mode, while omitting it selects detailed CSV export mode. A supplied domain is used only to match the Google Sheets tab and is never used in the Google Ads query. Each run accepts exactly one seed keyword. If Google Ads shows multiple plausible language or geographic matches, the skill pauses for the user to select one.

The bundled filter phrases are English. A non-English run requires localized blocked-phrase and buyer-intent files so English-only filtering is never applied silently. See [`references/keyword-filter-policy.md`](references/keyword-filter-policy.md) for the exact filtering order, boundary matching, and conservative brand policy.

## Sheets destination contract

The destination spreadsheet is fixed. The normalized domain must exactly match an existing visible tab; the skill never creates a spreadsheet or tab and never reuses the domain as a Google Ads website input.

The sheet contract validates the existing localized header strings exactly. Their English meanings and write behavior are:

| Column | Meaning | Write behavior |
| --- | --- | --- |
| A | Core keyword | New unique keyword idea |
| B | Target country | User-provided location text |
| C | Target customer | Copied from the latest complete template row |
| D | Related product URL | Copied from the latest complete template row |
| E | Publishing key | Copied only inside Google Sheets; never exported or reported |
| F | Publication status | Left blank |
| G | Publication time | Left blank |
| H | Published article URL | Left blank |

See [`references/sheet-contract.md`](references/sheet-contract.md) for the complete validation and write contract.

## CSV helper

Normalize a domain:

```bash
python3 scripts/keyword_workflow.py normalize-domain --domain "https://www.example.com/path"
```

Prepare a Google Ads CSV against an optional A-column keyword snapshot:

```bash
python3 scripts/keyword_workflow.py prepare \
  --ads-csv /path/to/keyword-ideas.csv \
  --seed "protein powder" \
  --language "English" \
  --existing-file /path/to/existing-keywords.json \
  --chunk-size 500 \
  --output /path/to/prepared.json
```

Create a filtered detailed CSV while preserving every Google Ads source column:

```bash
python3 scripts/keyword_workflow.py prepare \
  --ads-csv /path/to/keyword-ideas.csv \
  --seed "watch" \
  --language "English" \
  --detail-output /path/to/watch-google-ads-keywords.csv \
  --output /path/to/prepared.json
```

For a non-English run, also pass localized `--blocked-phrase-file` and `--buyer-intent-file` inputs. Use `--brand-file` to add one unambiguous, run-specific brand phrase per line. English runs automatically load the bundled filter lists.

The helper supports English and Chinese keyword headers, BOMs, UTF-16 tab-delimited exports, metadata rows before the CSV header, and punctuation-insensitive whole-token phrase matching. Detailed exports preserve all source metadata, headers, search-volume values, competition fields, low/high bid ranges, and any additional Google Ads columns. The helper reports separate counts for blocked phrases, confirmed brands, missing buyer intent, wrong-script English phrases, duplicates, and existing Sheet values.

## Validation

Run the unit tests:

```bash
python3 -m unittest discover -s tests -v
```

Validate the Codex skill structure:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

Do not commit downloaded Google Ads CSV files, local keyword snapshots, prepared outputs, publishing keys, or other operational data.
