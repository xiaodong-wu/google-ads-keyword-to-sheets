# Keyword filtering policy

## Defaults

- Language defaults to `English`.
- Location defaults to `All locations`.
- The Google Ads export order is preserved throughout filtering.

## Filtering pipeline

After parsing the Google Ads CSV, normalize each idea with NFKC and whitespace folding, then apply
these rules in order:

1. For English runs, reject phrases containing non-Latin letter scripts.
2. Reject the exact seed and within-export duplicates.
3. Reject phrases containing any entry from `blocked-phrases.txt`.
4. Reject phrases containing any entry from `confirmed-brands.txt` or a run-specific brand file.
5. Keep only phrases containing an entry from `buyer-intent-phrases.txt`.
6. In Sheets mode only, reject phrases already present in destination column A. Detailed export
   mode has no Sheet snapshot and retains every otherwise-qualified first occurrence.

Phrase matching is case-insensitive and punctuation-insensitive. Latin-script rules use whole token
boundaries: `sale` matches `watch sale` but not `wholesale watch`, while `near` matches `near me` and
`nearly` is represented by its own rule. Rules written in CJK, Hiragana, Katakana, Hangul, or Thai
use normalized phrase containment because those scripts may not include visible word spaces.

## Brand policy

The bundled brand file is intentionally conservative. Remove a run-specific term as a brand only
when the visible keyword makes the brand identity unambiguous. Keep ambiguous common words instead
of guessing. Put additional confirmed brands in a temporary one-phrase-per-line file and pass it
with `--brand-file`; never edit the Google Ads CSV by hand.

## Non-English runs

The bundled blocked and buyer-intent lists are English. For any other requested language, create
two conservative, localized, one-phrase-per-line temporary files and pass both
`--blocked-phrase-file` and `--buyer-intent-file`. Include localized equivalents of every blocked
concept and of the B2B/customization intent markers. The helper refuses a non-English run when
either localized list is missing, preventing an English-only policy from being applied silently.

The confirmed-brand list remains active for every language, and `--brand-file` can add localized or
run-specific brand spellings.
