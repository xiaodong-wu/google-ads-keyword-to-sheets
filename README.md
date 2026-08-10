# Google Ads Keyword Ideas to Google Sheets

A Codex skill that collects all unique English keyword ideas from the signed-in Google Ads Keyword Planner in Chrome and appends them to the matching domain tab in the configured **Automatically publish articles** Google Sheet.

The workflow uses the visible Google Ads interface and a one-time CSV export. It does not use the Google Ads API or generate keyword suggestions from another source.

## What it does

- Accepts one seed keyword, one geographic location, one domain, and an optional `dry-run` flag.
- Configures Keyword Planner for English, Google Search, the past 12 months, and the requested location.
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
$google-ads-keyword-to-sheets 关键词="protein powder" 地理位置="United States" 域名="www.nutricdmo.com" dry-run
```

Run the live workflow after reviewing the planned destination range:

```text
$google-ads-keyword-to-sheets 关键词="protein powder" 地理位置="United States" 域名="www.nutricdmo.com"
```

The domain defaults to `www.nutricdmo.com` when omitted. Each run accepts exactly one seed keyword. If Google Ads shows multiple plausible geographic matches, the skill pauses for the user to select one.

## Destination contract

The destination spreadsheet is fixed. The normalized domain must exactly match an existing visible tab; the skill never creates a spreadsheet or tab.

The expected A–H headers are:

| Column | Header | Write behavior |
| --- | --- | --- |
| A | 核心关键字 | New unique keyword idea |
| B | 目标国家 | User-provided location text |
| C | 目标客户 | Copied from the latest complete template row |
| D | 相关产品链接 | Copied from the latest complete template row |
| E | 发布密钥 | Copied only inside Google Sheets; never exported or reported |
| F | 发布状态 | Left blank |
| G | 发布时间 | Left blank |
| H | 新发布文章链接 | Left blank |

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
