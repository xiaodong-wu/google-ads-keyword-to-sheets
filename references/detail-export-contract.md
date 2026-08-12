# Detailed CSV export contract

Use this contract only when the user did not provide a domain.

## Destination and format

- Create one durable `.csv` file in the active workspace, not only in a temporary directory.
- Use a descriptive filename based on the seed, such as `watch-google-ads-keywords.csv`. Replace
  unsafe filename characters and avoid overwriting an unrelated existing file.
- Write UTF-8 with a BOM for spreadsheet compatibility.
- Never access Google Drive or Google Sheets in this mode.

## Preserved structure

- Preserve every Google Ads metadata row before the detected keyword header, including currency or
  targeting context.
- Preserve the complete source header in its original column order.
- For every retained keyword, preserve its complete original source row in the same column order.
- Keep all available metrics, including average monthly searches, recent and yearly change,
  competition, competition index, low-range top-of-page bid, high-range top-of-page bid, and any
  additional Google Ads columns.
- Never calculate, translate, round, sort, merge, or fill missing metric values.

Before exporting, require the source header to visibly contain the keyword, average monthly search
volume, competition, low bid range, and high bid range columns. Header wording may be localized;
verify by meaning rather than guessing from an unfamiliar label. Stop and report any missing
required metric instead of inventing it.

## Filtering and row identity

Apply `references/keyword-filter-policy.md` to the keyword column only. Retain the exact full source
row selected by each surviving keyword. For duplicate keywords, retain the first source row in
Google Ads relevance order. Do not deduplicate against an online Sheet in this mode.

## Verification

After writing, reopen the CSV and verify:

1. Metadata rows and the full header match the source export.
2. The number of detail rows equals `detail_row_count`.
3. Keyword order equals `new_keywords`.
4. Every detail cell exactly matches the corresponding source row.
5. The output contains no Sheet publishing key or other Sheet-only data.

When no keyword survives, emit the preserved metadata rows and complete header with zero detail
rows so the user receives a valid, auditable result.
