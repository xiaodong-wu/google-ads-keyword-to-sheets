# Keyword filtering policy

## Defaults

- Language defaults to `English`.
- Location defaults to `All locations`.
- Preserve Google Ads relevance order.
- Do not require wholesale, bulk-purchase, B2B, supplier, manufacturer, or customization markers.

## Filtering pipeline

After parsing the Google Ads CSV, normalize each idea with NFKC and whitespace folding, then apply
these rules in order:

1. For English runs, reject phrases containing non-Latin letter scripts.
2. Reject the exact seed and within-export duplicates.
3. Reject phrases containing any entry from `blocked-phrases.txt`.
4. Reject phrases containing any entry from `confirmed-brands.txt` or a run-specific brand file.
5. Reject exact full keywords listed in the run-specific imprecise-keyword file.
6. In Sheets mode only, reject phrases already present in destination column A. Detailed export
   mode has no Sheet snapshot and retains every otherwise-qualified first occurrence.

Phrase matching is case-insensitive and punctuation-insensitive. Latin-script rules use whole-token
boundaries: `me` matches `best for me` but not `metal`, and `old` matches `old watch` but
not `gold watch`. Rules written in CJK, Hiragana, Katakana, Hangul, or Thai use normalized phrase
containment because those scripts may not include visible word spaces.

## Precision policy

Review the exported ideas after blocked-phrase and brand filtering. Keep ideas that are directly
about the seed product, service, category, or an unambiguous close synonym. Remove ideas that shift
to another product, a broad adjacent topic, a different user need, or a term whose relationship to
the seed is uncertain.

Record each imprecise idea as its complete visible keyword, one per line, in a temporary file and
pass it with `--irrelevant-keyword-file`. Exact full-keyword matching prevents a rejected generic
idea from accidentally removing a longer, precise idea that contains some of the same words. When
no imprecise idea remains, pass an empty file so the review is still auditable.

## Brand policy

The bundled brand file is intentionally conservative. Remove a run-specific term as a brand only
when the visible keyword makes the brand identity unambiguous. Keep ambiguous common words instead
of guessing. Put additional confirmed brands in a temporary one-phrase-per-line file and pass it
with `--brand-file`; never edit the Google Ads CSV by hand.

## Non-English runs

The bundled blocked list is English. For another requested language, create a conservative,
localized, one-phrase-per-line file covering the concepts in the bundled list and pass it with
`--blocked-phrase-file`. The helper refuses a non-English run when this file is missing.

The confirmed-brand list remains active for every language. Use `--brand-file` for localized or
run-specific brand spellings and `--irrelevant-keyword-file` for exact imprecise keywords.
