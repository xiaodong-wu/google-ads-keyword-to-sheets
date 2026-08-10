---
name: google-ads-keyword-to-sheets
description: Fetch all unique English keyword ideas from the signed-in Google Ads Keyword Planner in Chrome using one seed keyword, a geographic location, and a domain, then append them to the matching domain tab in the configured Automatically publish articles Google Sheet. Use when Codex must run or dry-run this exact Google Ads-to-Sheets keyword collection workflow, including CSV export parsing, existing-keyword deduplication, A-E template propagation, and verified batch writes.
---

# Google Ads Keyword Ideas To Sheets

Run one auditable Keyword Planner-to-Sheets job. Accept exactly one `关键词`, one `地理位置`, one
`域名`, and optional `dry-run`. Default the domain to `www.nutricdmo.com` only when it is omitted.
Treat an explicit request without `dry-run` as authorization to submit the Keyword Planner query,
download its CSV, and append verified rows to the configured Sheet.

## Required reading

- Read [references/sheet-contract.md](references/sheet-contract.md) before reading or writing the
  spreadsheet.
- Load and follow `chrome:control-chrome` before any Google Ads browser action.
- Load and follow `google-drive:google-drive` and `google-drive:google-sheets` before any Sheet
  operation. Read their existing-edit, live-read, native-cell, batch-update, and visual-verification
  references required for the operation.

## Workflow

1. **Validate inputs**
   - Require one non-empty seed keyword and geographic location. Reject a keyword list.
   - Normalize the domain with:
     `python scripts/keyword_workflow.py normalize-domain --domain '<domain>'`.
   - Build the website seed as `https://<normalized-domain>/`.
   - Create a temporary run directory with `mktemp -d`. Keep only the Google Ads CSV, an A-column-only
     existing-keyword snapshot, parser output, and non-secret counts there. Never place columns C-E
     or a publishing key in local files, logs, commands, or reports.

2. **Ground the destination Sheet**
   - Use the fixed spreadsheet and exact schema in `references/sheet-contract.md`.
   - Read metadata first. Require the exact spreadsheet title and an exact visible tab whose title
     equals the normalized domain. Never create or guess a tab.
   - Read row 1 with cell metadata and require all eight headers in order.
   - Read bounded A-column chunks to find the last non-empty keyword row and existing keywords. Save
     only the A-column strings to a temporary JSON array.
   - Read bounded C:E chunks from the populated edge upward. Select the latest row whose C, D, and E
     are all non-empty as the template. Treat E as secret and never repeat its value.

3. **Run Google Ads Keyword Planner in Chrome**
   - Name the Chrome session, then reuse or claim a signed-in `ads.google.com` Keyword Planner tab.
     If none exists, open `https://ads.google.com/aw/keywordplanner/home` in Chrome.
   - If sign-in blocks the page, leave the tab as a handoff and ask the user to sign in in Chrome.
     Follow the Chrome skill for CAPTCHA or permission prompts.
   - Open **Discover new keywords** or edit the current keyword/website query. Select **Start with
     keywords**. Remove previous keyword chips, enter the one exact seed keyword, and fill the
     website-filter field with the website seed.
   - Set the geographic target to the requested location. Require one exact visible match; when
     multiple plausible canonical matches remain, ask the user to choose instead of guessing.
   - Set targeting language to English, network to Google, date range to the past 12 months, and
     retain the adult-content exclusion.
   - Submit **Get results**. Verify the visible seed, location, English targeting, Google network,
     date range, and a non-zero available-ideas count before exporting.
   - Treat an account-revoked banner as a warning only when query and export controls still work.
     If an ad-blocker or account-state dialog prevents either action, stop and tell the user exactly
     what must be fixed.

4. **Download and prepare all ideas**
   - Open **Download keyword ideas**, start `waitForEvent("download")`, choose `.csv`, await the
     download, and obtain its local path with `download.path({timeoutMs: 30000})`.
   - Run:

     ```bash
     python scripts/keyword_workflow.py prepare \
       --ads-csv <downloaded-csv> \
       --seed <exact-seed-keyword> \
       --existing-file <a-column-only-json> \
       --chunk-size 500 \
       --output <prepared-json>
     ```

   - Use `new_keywords` exactly in output order. Do not sort by volume or competition. The script
     excludes the seed, non-English phrases, within-export duplicates, and existing A-column values.
   - If `new_count` is zero, do not write and report the exclusion counts.

5. **Plan or write the Sheet**
   - Immediately re-read column A before a live write, regenerate the A-only snapshot, and rerun the
     parser so concurrent additions are excluded.
   - Set the first destination row to one after the last non-empty A cell. Require F:H to be blank
     across every planned destination row; stop rather than clear unrelated values.
   - When the required last row exceeds `gridProperties.rowCount`, append exactly the missing number
     of rows before writing.
   - In `dry-run`, stop here. Report the spreadsheet, tab, template row number, planned destination
     range, parser counts, and zero writes. Never call a Sheet mutation tool.
   - In a live run, process `chunks` in order, at most 500 rows per call. For each chunk:
     1. `copyPaste` template A:E to the destination A:E with `PASTE_NORMAL`.
     2. `updateCells` destination A:B with keyword and the user's geographic-location text, using
        the precise `userEnteredValue` field mask.
     3. Leave F:H untouched and blank.
   - Re-read each written A:H chunk with values, formats, validation, and formulas. Verify every A/B
     value, copied C-E structure, blank F-H cells, and matching row formatting before advancing.
   - If a chunk fails or mismatches, stop. Report only verified committed ranges and non-secret
     counts. A rerun is safe because the parser excludes existing A values.

6. **Finish and report**
   - Apply the Google Sheets visual-quality check to the appended rows and nearby cells. Do not
     resize or restyle the sheet unless the new values are visibly clipped and a minimal targeted
     fix is required.
   - Finalize Chrome tabs according to the Chrome skill. Keep only a user-facing handoff or an
     explicitly useful deliverable tab.
   - Report the seed, normalized domain, location, exported count, exclusion counts, appended count,
     verified ranges, and the observed spreadsheet URL. Never report column E or its value.

## Failure rules

- Do not fall back to web search, invented suggestions, or Google Ads API results.
- Do not write when the spreadsheet title, domain tab, headers, template row, destination emptiness,
  browser targeting, CSV header, or readback verification is uncertain.
- Do not create a new spreadsheet or tab and do not modify F:H.
- Preserve the downloaded relevance order and make partial progress idempotent through A-column
  deduplication.
