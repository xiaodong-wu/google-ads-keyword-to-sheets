---
name: google-ads-keyword-to-sheets
description: Fetch Google Ads Keyword Planner ideas for one seed, optional language, and optional geographic location, then remove low-value phrases such as near, me, price, cost, and old, confirmed brands, and topically imprecise ideas. When a domain is provided, append unique keywords to its matching tab in the configured Automatically publish articles Google Sheet. When no domain is provided, export a filtered local CSV that retains search volume, competition, bid ranges, and every other Google Ads source column. Language defaults to English and location defaults to All locations. Never use the domain as a Google Ads website seed or site filter. Use for live runs, dry-runs, detailed keyword exports, or updates to this workflow.
---

# Precise Google Ads Keyword Ideas to Sheets or CSV

Run one auditable Keyword Planner job. Accept exactly one `keyword`, optional `language`, optional
`location`, optional `domain`, and optional `dry-run`. Default `language` to `English` and
`location` to `All locations`. Do not default a missing domain.

Choose the output mode solely from whether the user explicitly provided `domain`:

- **Sheets mode:** with `domain`, select the destination Sheet tab.
  Use the domain only to normalize and select the destination Sheet tab.
  Never send the domain or a derived URL to Google Ads.
- **Detailed export mode:** without `domain`, do not access Google Drive or Google Sheets. Export a
  filtered CSV containing each retained keyword and all of its original Google Ads metrics.

Treat a Sheets-mode request without `dry-run` as authorization to submit the query, download the
CSV, and append verified rows. In detailed export mode, `dry-run` plans but does not create the
local CSV.

## Required reading

- Read [references/keyword-filter-policy.md](references/keyword-filter-policy.md) before parsing.
- In detailed export mode, read
  [references/detail-export-contract.md](references/detail-export-contract.md).
- In Sheets mode, read [references/sheet-contract.md](references/sheet-contract.md), then load and
  follow `google-drive:google-drive` and `google-drive:google-sheets` before any Sheet operation.
  Read their required existing-edit, live-read, native-cell, batch-update, and visual-verification
  references.
- Load and follow `chrome:control-chrome` before any Google Ads browser action.

## Workflow

1. **Validate inputs and choose the mode**
   - Require one non-empty seed keyword and reject a keyword list.
   - Resolve omitted language to `English` and omitted location to `All locations`.
   - When `domain` is present, normalize it only for tab matching with:
     `python3 scripts/keyword_workflow.py normalize-domain --domain '<domain>'`.
   - When `domain` is absent, select detailed export mode. Never substitute
     `www.nutricdmo.com` or any other default domain.
   - Create a temporary run directory with `mktemp -d`. Keep the source Ads CSV, parser JSON,
     localized filter files, optional confirmed-brand addendum, the required run-specific
     imprecise-keyword file, and—only in Sheets mode—an A-column-only keyword snapshot there.
   - In detailed export mode, choose a durable workspace path ending in `.csv` for the final file.
     Do not place the final deliverable only in a temporary directory.

2. **Ground the destination only in Sheets mode**
   - Use the fixed spreadsheet and schema in `references/sheet-contract.md`.
   - Read metadata first. Require the exact title and an exact visible tab whose title equals the
     normalized domain. Never create or guess a tab.
   - Read row 1 with cell metadata and require all eight headers in order.
   - Read bounded A-column chunks to find existing keywords and the last populated keyword row.
     Save only A-column strings to the temporary snapshot.
   - Read bounded C:E chunks from the populated edge upward. Select the latest row whose C, D, and
     E are all non-empty as the template. Treat E as secret and never repeat its value.

3. **Run Google Ads Keyword Planner in Chrome**
   - Name the Chrome session, then reuse or claim a signed-in `ads.google.com` Keyword Planner tab.
     If none exists, open `https://ads.google.com/aw/keywordplanner/home`.
   - If sign-in blocks the page, leave the tab as a handoff and ask the user to sign in. Follow the
     Chrome skill for CAPTCHA and permission prompts.
   - Open **Discover new keywords**, select **Start with keywords**, remove previous keyword chips,
     and enter the one exact seed.
   - Clear the optional website-filter field if it contains any value and leave it empty. Never
     enter the normalized domain, a derived URL, or another website into Google Ads.
   - Set the requested location. For `All locations`, remove every specific location chip and
     verify the visible all-locations state. Otherwise require one exact visible match and ask the
     user when multiple plausible canonical matches remain.
   - Set targeting language to the requested language. Require one exact visible match. Set network
     to Google, date range to the past 12 months, and retain adult-content exclusion.
   - Submit **Get results**. Verify the seed, location, language, Google network, date range, no
     active website/site filter, and a non-zero available-ideas count before exporting.
   - Treat an account-revoked banner as a warning only when query and export controls still work.
     Stop when an ad blocker, dialog, or account state prevents the query or export.

4. **Download and filter all ideas**
   - Open **Download keyword ideas**, start `waitForEvent("download")`, choose `.csv`, await the
     download, and get its local path with `download.path({timeoutMs: 30000})`.
   - Use the bundled English blocked-phrase list for English. For another language, create a
     complete localized blocked-phrase file according to
     `references/keyword-filter-policy.md`.
   - Inspect ideas for additional unambiguous brands. If found, put one confirmed brand phrase per
     line in a temporary file and pass it with `--brand-file`. Keep ambiguous terms.
   - Review every remaining idea for topical precision. Keep only ideas directly about the seed
     product, service, category, or an unambiguous close synonym. Put each broad, adjacent,
     different-intent, or uncertain full keyword into a temporary one-keyword-per-line file and
     pass it with `--irrelevant-keyword-file`. Pass an empty file when every remaining idea is
     precise.
   - Preserve Google Ads relevance order. Never sort or recompute search volume, competition, bid,
     trend, or other metrics.

5. **Prepare the selected output**

   In Sheets mode, run:

   ```bash
   python3 scripts/keyword_workflow.py prepare \
     --ads-csv <downloaded-csv> \
     --seed <exact-seed-keyword> \
     --language <requested-language> \
     --existing-file <a-column-only-json> \
     --irrelevant-keyword-file <exact-imprecise-keywords.txt> \
     --chunk-size 500 \
     --output <prepared-json>
   ```

   In detailed export mode, read `references/detail-export-contract.md`, then run:

   ```bash
   python3 scripts/keyword_workflow.py prepare \
     --ads-csv <downloaded-csv> \
     --seed <exact-seed-keyword> \
     --language <requested-language> \
     --irrelevant-keyword-file <exact-imprecise-keywords.txt> \
     --detail-output <durable-workspace-path.csv> \
     --output <prepared-json>
   ```

   For non-English runs, add the localized `--blocked-phrase-file`. Add `--brand-file` when
   needed. During a detailed-export `dry-run`, omit `--detail-output` and report the planned
   path.

   The helper excludes the seed, wrong-script English phrases, within-export duplicates, blocked
   phrases, confirmed brands, and exact run-specific imprecise keywords. It does not require a
   wholesale, bulk, supplier, manufacturer, or customization marker. Sheets mode also excludes
   existing A-column values. Matching uses normalized boundaries, so `me` does not match
   `metal`, `near` does not match `nearly`, and `old` does not match `gold`.

6. **Complete Sheets mode**
   - Immediately re-read A before a live write, refresh the snapshot, and rerun the parser.
   - Append after the last non-empty A cell. Require F:H to be blank across every destination row.
     Append exactly the missing grid rows when capacity is insufficient.
   - In `dry-run`, report the tab, template row, planned range, counts, and zero writes. Never call a
     mutation tool.
   - In a live run, process at most 500 rows per batch: copy the template A:E with `PASTE_NORMAL`,
     overwrite A:B with keyword and resolved location using `userEnteredValue`, and leave F:H blank.
   - Re-read each A:H chunk with values, formats, validation, and formulas. Verify every A/B value,
     copied C:E structure, blank F:H cells, and row formatting before continuing.
   - If `new_count` is zero, do not write. Report exclusion counts.

7. **Complete detailed export mode**
   - Do not call any Google Drive or Google Sheets read or mutation tool.
   - Reopen the generated CSV and verify its metadata rows, complete source header, filtered row
     count, keyword order, and all per-keyword metric cells against the source export.
   - If `new_count` is zero in a live run, still deliver the valid metadata-and-header-only CSV and
     clearly report that no keyword rows survived.
   - Return a clickable link to the local CSV and report its row and column counts.

8. **Finish and report**
   - Finalize Chrome tabs according to the Chrome skill.
   - Report seed, language, location, source count, every exclusion count—including topically
     imprecise ideas—and retained count.
   - In Sheets mode, also report normalized domain, appended count, verified ranges, and observed
     spreadsheet URL without exposing column E.
   - In detailed export mode, report the local file path, retained detail rows, and preserved source
     columns. Never claim online writes.

## Failure rules

- Do not fall back to web search, invented ideas, or Google Ads API results.
- Do not submit or export while a website/site filter is active.
- Do not write when browser targeting, CSV header, filter localization, brand judgment, or topical
  precision is uncertain.
- In Sheets mode, also stop when the spreadsheet title, tab, headers, template, destination
  emptiness, or readback is uncertain. Do not create a Sheet or tab and do not modify F:H.
- In detailed export mode, do not discard, transform, estimate, or merge metric values. Do not
  overwrite the source Ads CSV or an unrelated existing file.
- Preserve relevance order and make Sheets-mode partial progress idempotent through A-column
  deduplication.
