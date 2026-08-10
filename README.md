# Google Ads Keyword Ideas to Google Sheets

A Codex skill that collects all unique English keyword ideas from the signed-in Google Ads Keyword Planner in Chrome and appends them to the matching domain tab in the configured **Automatically publish articles** Google Sheet.

The workflow uses the visible Google Ads interface and a one-time CSV export. It does not use the Google Ads API or generate keyword suggestions from another source.

The supplied domain is a destination-tab selector only. The skill never enters it, or a URL derived from it, into the Google Ads website filter.

## What it does

- Accepts one seed keyword, one geographic location, one destination-tab domain, and an optional `dry-run` flag.
- Configures Keyword Planner for English, Google Search, the past 12 months, and the requested location, with no website/site filter.
- Downloads all keyword ideas as CSV and preserves Google Ads relevance order.
- Normalizes text with NFKC, removes duplicate ideas, excludes the seed keyword, filters non-Latin-script phrases, and removes keywords already present in the destination tab.
- Appends at most 500 rows per batch and verifies every written range.
- Copies the latest complete C–E template row inside Google Sheets, writes the keyword and location to A–B, and leaves F–H blank.
- Keeps the publishing key inside Google Sheets and out of local files, logs, commands, and reports.

## Requirements

- Codex Desktop with access to the Chrome, Google Drive, and Google Sheets integrations.
- A Chrome session signed in to an account that can use Google Ads Keyword Planner and export keyword ideas.
- Access to the configured Google Sheet and an existing tab whose name exactly matches the normalized domain.
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
$google-ads-keyword-to-sheets keyword="protein powder" location="United States" domain="www.nutricdmo.com" dry-run
```

Run the live workflow after reviewing the planned destination range:

```text
$google-ads-keyword-to-sheets keyword="protein powder" location="United States" domain="www.nutricdmo.com"
```

The domain defaults to `www.nutricdmo.com` when omitted and is used only to match the Google Sheets tab. It is not used in the Google Ads query. Each run accepts exactly one seed keyword. If Google Ads shows multiple plausible geographic matches, the skill pauses for the user to select one.

## Destination contract

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
  --existing-file /path/to/existing-keywords.json \
  --chunk-size 500 \
  --output /path/to/prepared.json
```

The helper supports English and Chinese keyword headers, BOMs, UTF-16 tab-delimited exports, and metadata rows before the CSV header.

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
