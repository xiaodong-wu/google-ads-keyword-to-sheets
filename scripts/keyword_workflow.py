#!/usr/bin/env python3
"""Normalize domains and prepare high-intent Google Ads keyword ideas."""

import argparse
import csv
import io
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit


REQUIRED_HEADERS: Tuple[str, ...] = (
    "核心关键字",
    "目标国家",
    "目标客户",
    "相关产品链接",
    "发布密钥",
    "发布状态",
    "发布时间",
    "新发布文章链接",
)

KEYWORD_HEADER_ALIASES = {
    "keyword",
    "keywords",
    "keyword idea",
    "keyword ideas",
    "search term",
    "关键字",
    "关键词",
    "关键字提示",
    "关键词提示",
}

NON_ENGLISH_SCRIPT_MARKERS = (
    "CJK",
    "HIRAGANA",
    "KATAKANA",
    "HANGUL",
    "CYRILLIC",
    "ARABIC",
    "HEBREW",
    "THAI",
    "DEVANAGARI",
    "GREEK",
)

DEFAULT_LANGUAGE = "English"
DEFAULT_LOCATION = "All locations"
SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BLOCKED_PHRASES_FILE = SKILL_ROOT / "references" / "blocked-phrases.txt"
DEFAULT_BUYER_INTENT_PHRASES_FILE = SKILL_ROOT / "references" / "buyer-intent-phrases.txt"
DEFAULT_CONFIRMED_BRANDS_FILE = SKILL_ROOT / "references" / "confirmed-brands.txt"


class KeywordWorkflowError(ValueError):
    """Raised when an input cannot be handled safely."""


def normalize_text(value: Any) -> str:
    """Normalize visible keyword text while preserving its original word order."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    return " ".join(text.split()).strip()


def dedupe_key(value: Any) -> str:
    return normalize_text(value).casefold()


def phrase_key(value: Any) -> str:
    """Normalize punctuation and spacing for whole-token phrase matching."""
    text = dedupe_key(value)
    normalized = "".join(char if char.isalnum() else " " for char in text)
    return " ".join(normalized.split())


def uses_unsegmented_script(value: Any) -> bool:
    """Return true for scripts whose phrases may not have visible word spaces."""
    markers = ("CJK", "HIRAGANA", "KATAKANA", "HANGUL", "THAI")
    return any(
        any(marker in unicodedata.name(char, "") for marker in markers)
        for char in normalize_text(value)
        if char.isalpha()
    )


def contains_phrase(value: Any, phrase: Any) -> bool:
    """Match Latin phrases on token boundaries and unsegmented scripts by phrase."""
    value_key = phrase_key(value)
    phrase_value = phrase_key(phrase)
    if not value_key or not phrase_value:
        return False
    if uses_unsegmented_script(phrase):
        return phrase_value in value_key
    return " {} ".format(phrase_value) in " {} ".format(value_key)


def contains_any_phrase(value: Any, phrases: Iterable[str]) -> bool:
    return any(contains_phrase(value, phrase) for phrase in phrases)


def is_english_language(language: Any) -> bool:
    return dedupe_key(language) in {"english", "en", "en us", "en gb"}


def normalize_header(value: Any) -> str:
    return normalize_text(value).strip("\ufeff").casefold()


def normalize_domain(raw_domain: str) -> str:
    """Return a lowercase ASCII hostname while preserving a leading www label."""
    candidate = normalize_text(raw_domain)
    if not candidate:
        raise KeywordWorkflowError("Domain is required")
    if "://" not in candidate:
        candidate = "https://" + candidate
    parsed = urlsplit(candidate)
    if parsed.scheme.casefold() not in {"http", "https"}:
        raise KeywordWorkflowError("Domain must use http or https")
    if parsed.username or parsed.password:
        raise KeywordWorkflowError("Domain must not contain credentials")
    try:
        port = parsed.port
    except ValueError as exc:
        raise KeywordWorkflowError("Domain contains an invalid port") from exc
    if port is not None:
        raise KeywordWorkflowError("Domain must not contain a port")
    hostname = (parsed.hostname or "").strip(".").casefold()
    if not hostname:
        raise KeywordWorkflowError("Domain does not contain a hostname")
    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise KeywordWorkflowError("Domain cannot be converted to an ASCII hostname") from exc
    if len(hostname) > 253 or "." not in hostname:
        raise KeywordWorkflowError("Domain must be a fully qualified hostname")
    label_pattern = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
    if any(not label_pattern.fullmatch(label) for label in hostname.split(".")):
        raise KeywordWorkflowError("Domain contains an invalid hostname label")
    return hostname


def is_english_keyword(value: str) -> bool:
    """Accept Latin-script ideas and reject ideas containing other letter scripts."""
    has_latin_letter = False
    for char in value:
        if not char.isalpha():
            continue
        name = unicodedata.name(char, "")
        if "LATIN" in name:
            has_latin_letter = True
            continue
        if any(marker in name for marker in NON_ENGLISH_SCRIPT_MARKERS):
            return False
        return False
    return has_latin_letter


def decode_csv_bytes(raw: bytes) -> str:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise KeywordWorkflowError("CSV encoding is not supported")


def read_csv_rows(path: Path) -> List[List[str]]:
    text = decode_csv_bytes(path.read_bytes())
    sample = text[:16384]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
    return [list(row) for row in csv.reader(io.StringIO(text), dialect)]


def is_keyword_header(value: Any) -> bool:
    normalized = normalize_header(value)
    if normalized in KEYWORD_HEADER_ALIASES:
        return True
    return normalized.startswith("keyword (") or normalized.startswith("关键字（")


def locate_keyword_column(rows: Sequence[Sequence[str]]) -> Tuple[int, int]:
    """Return zero-based header row and keyword column indexes."""
    for row_index, row in enumerate(rows):
        nonempty_cells = sum(1 for cell in row if normalize_text(cell))
        if nonempty_cells < 2:
            continue
        for column_index, cell in enumerate(row):
            if is_keyword_header(cell):
                return row_index, column_index
    raise KeywordWorkflowError("Could not find a supported keyword column header")


def parse_ads_csv_table(path: Path) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """Parse an Ads export without discarding its metadata or metric columns."""
    rows = read_csv_rows(path)
    header_row, keyword_column = locate_keyword_column(rows)
    data_rows: List[List[str]] = []
    empty_count = 0
    for row in rows[header_row + 1 :]:
        value = row[keyword_column] if keyword_column < len(row) else ""
        if not normalize_text(value):
            empty_count += 1
            continue
        data_rows.append(list(row))
    table = {
        "preamble_rows": [list(row) for row in rows[:header_row]],
        "headers": list(rows[header_row]),
        "data_rows": data_rows,
        "keyword_column": keyword_column,
    }
    return table, {
        "header_row": header_row + 1,
        "keyword_column": keyword_column + 1,
        "column_count": len(rows[header_row]),
        "empty_excluded": empty_count,
    }


def parse_ads_csv(path: Path) -> Tuple[List[str], Dict[str, int]]:
    table, stats = parse_ads_csv_table(path)
    keyword_column = table["keyword_column"]
    keywords = [normalize_text(row[keyword_column]) for row in table["data_rows"]]
    return keywords, stats


def _flatten_existing_json(value: Any) -> List[str]:
    if isinstance(value, dict) and "values" in value:
        value = value["values"]
    if not isinstance(value, list):
        raise KeywordWorkflowError("Existing-keyword JSON must be a list or contain a values list")
    result: List[str] = []
    for item in value:
        if isinstance(item, list):
            if item:
                result.append(normalize_text(item[0]))
        elif isinstance(item, str):
            result.append(normalize_text(item))
        elif item is not None:
            result.append(normalize_text(item))
    return [item for item in result if item]


def load_existing_keywords(path: Optional[Path]) -> List[str]:
    if path is None:
        return []
    text = path.read_text(encoding="utf-8-sig")
    try:
        return _flatten_existing_json(json.loads(text))
    except json.JSONDecodeError:
        rows = list(csv.reader(io.StringIO(text)))
        return [normalize_text(row[0]) for row in rows if row and normalize_text(row[0])]


def load_phrase_file(path: Path) -> List[str]:
    """Load one phrase per line, ignoring blank lines and comments."""
    phrases: List[str] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = normalize_text(raw_line)
        if not line or line.startswith("#"):
            continue
        phrases.append(line)
    return phrases


def merge_phrases(*groups: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for group in groups:
        for phrase in group:
            normalized = phrase_key(phrase)
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalize_text(phrase))
    return result


def resolve_filter_phrases(
    language: str,
    blocked_phrases: Optional[Iterable[str]] = None,
    buyer_intent_phrases: Optional[Iterable[str]] = None,
    confirmed_brands: Optional[Iterable[str]] = None,
) -> Tuple[List[str], List[str], List[str]]:
    """Resolve bundled English rules or require explicit localized rules."""
    if is_english_language(language):
        default_blocked = load_phrase_file(DEFAULT_BLOCKED_PHRASES_FILE)
        default_intent = load_phrase_file(DEFAULT_BUYER_INTENT_PHRASES_FILE)
    else:
        default_blocked = []
        default_intent = []
        if blocked_phrases is None or buyer_intent_phrases is None:
            raise KeywordWorkflowError(
                "Non-English runs require localized blocked-phrase and buyer-intent files"
            )
    default_brands = load_phrase_file(DEFAULT_CONFIRMED_BRANDS_FILE)
    return (
        merge_phrases(default_blocked, blocked_phrases or []),
        merge_phrases(default_intent, buyer_intent_phrases or []),
        merge_phrases(default_brands, confirmed_brands or []),
    )


def chunk_items(items: Sequence[str], chunk_size: int) -> List[List[str]]:
    if chunk_size <= 0:
        raise KeywordWorkflowError("Chunk size must be positive")
    return [list(items[index : index + chunk_size]) for index in range(0, len(items), chunk_size)]


def select_keyword_ideas(
    exported_keywords: Sequence[str],
    seed: str,
    existing_keywords: Iterable[str],
    language: str = DEFAULT_LANGUAGE,
    blocked_phrases: Optional[Iterable[str]] = None,
    buyer_intent_phrases: Optional[Iterable[str]] = None,
    confirmed_brands: Optional[Iterable[str]] = None,
) -> Tuple[List[str], List[int], Dict[str, Any]]:
    """Return filtered keywords, their source indexes, and exclusion counts."""
    seed_key = dedupe_key(seed)
    if not seed_key:
        raise KeywordWorkflowError("Seed keyword is required")
    target_language = normalize_text(language) or DEFAULT_LANGUAGE
    active_blocked, active_intent, active_brands = resolve_filter_phrases(
        target_language,
        blocked_phrases=blocked_phrases,
        buyer_intent_phrases=buyer_intent_phrases,
        confirmed_brands=confirmed_brands,
    )
    if not active_intent:
        raise KeywordWorkflowError("Buyer-intent phrase list cannot be empty")
    header_keys = {dedupe_key(header) for header in REQUIRED_HEADERS}
    existing_keys = {dedupe_key(value) for value in existing_keywords if dedupe_key(value)}
    existing_keys.difference_update(header_keys)
    seen_export: set = set()
    new_keywords: List[str] = []
    selected_indices: List[int] = []
    counts = {
        "parsed_count": 0,
        "non_english_excluded": 0,
        "seed_excluded": 0,
        "duplicate_export_excluded": 0,
        "blocked_phrase_excluded": 0,
        "confirmed_brand_excluded": 0,
        "buyer_intent_excluded": 0,
        "existing_excluded": 0,
    }
    for source_index, raw_keyword in enumerate(exported_keywords):
        keyword = normalize_text(raw_keyword)
        if not keyword:
            continue
        counts["parsed_count"] += 1
        keyword_key = dedupe_key(keyword)
        if is_english_language(target_language) and not is_english_keyword(keyword):
            counts["non_english_excluded"] += 1
            continue
        if keyword_key == seed_key:
            counts["seed_excluded"] += 1
            continue
        if keyword_key in seen_export:
            counts["duplicate_export_excluded"] += 1
            continue
        seen_export.add(keyword_key)
        if contains_any_phrase(keyword, active_blocked):
            counts["blocked_phrase_excluded"] += 1
            continue
        if contains_any_phrase(keyword, active_brands):
            counts["confirmed_brand_excluded"] += 1
            continue
        if not contains_any_phrase(keyword, active_intent):
            counts["buyer_intent_excluded"] += 1
            continue
        if keyword_key in existing_keys:
            counts["existing_excluded"] += 1
            continue
        new_keywords.append(keyword)
        selected_indices.append(source_index)
    return new_keywords, selected_indices, {**counts, "language": target_language}


def build_prepared_result(
    new_keywords: Sequence[str], counts: Dict[str, Any], chunk_size: int
) -> Dict[str, Any]:
    chunks = chunk_items(new_keywords, chunk_size)
    return {
        "stats": {
            **counts,
            "new_count": len(new_keywords),
            "chunk_count": len(chunks),
            "chunk_size": chunk_size,
        },
        "new_keywords": new_keywords,
        "chunks": chunks,
    }


def prepare_keyword_ideas(
    exported_keywords: Sequence[str],
    seed: str,
    existing_keywords: Iterable[str],
    chunk_size: int = 500,
    language: str = DEFAULT_LANGUAGE,
    blocked_phrases: Optional[Iterable[str]] = None,
    buyer_intent_phrases: Optional[Iterable[str]] = None,
    confirmed_brands: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    new_keywords, _, counts = select_keyword_ideas(
        exported_keywords,
        seed=seed,
        existing_keywords=existing_keywords,
        language=language,
        blocked_phrases=blocked_phrases,
        buyer_intent_phrases=buyer_intent_phrases,
        confirmed_brands=confirmed_brands,
    )
    return build_prepared_result(new_keywords, counts, chunk_size)


def prepare_ads_table(
    table: Dict[str, Any],
    seed: str,
    existing_keywords: Iterable[str],
    chunk_size: int = 500,
    language: str = DEFAULT_LANGUAGE,
    blocked_phrases: Optional[Iterable[str]] = None,
    buyer_intent_phrases: Optional[Iterable[str]] = None,
    confirmed_brands: Optional[Iterable[str]] = None,
) -> Tuple[Dict[str, Any], List[List[str]]]:
    """Filter a parsed Ads table while retaining every source metric column."""
    keyword_column = table["keyword_column"]
    data_rows = table["data_rows"]
    keywords = [normalize_text(row[keyword_column]) for row in data_rows]
    new_keywords, selected_indices, counts = select_keyword_ideas(
        keywords,
        seed=seed,
        existing_keywords=existing_keywords,
        language=language,
        blocked_phrases=blocked_phrases,
        buyer_intent_phrases=buyer_intent_phrases,
        confirmed_brands=confirmed_brands,
    )
    prepared = build_prepared_result(new_keywords, counts, chunk_size)
    filtered_rows = [list(data_rows[index]) for index in selected_indices]
    return prepared, filtered_rows


def validate_headers(headers: Sequence[Any]) -> None:
    actual = tuple(normalize_text(value) for value in headers[: len(REQUIRED_HEADERS)])
    if actual != REQUIRED_HEADERS:
        raise KeywordWorkflowError("Spreadsheet headers do not match the required A:H contract")


def find_latest_template_row(rows: Sequence[Sequence[Any]], first_sheet_row: int = 2) -> int:
    """Return the 1-based latest row whose C:E cells are non-empty."""
    for offset in range(len(rows) - 1, -1, -1):
        row = rows[offset]
        if len(row) >= 5 and all(normalize_text(row[index]) for index in (2, 3, 4)):
            return first_sheet_row + offset
    raise KeywordWorkflowError("No complete C:E template row was found")


def find_last_keyword_row(rows: Sequence[Sequence[Any]], first_sheet_row: int = 1) -> int:
    """Return the 1-based last row with a non-empty first cell, or zero if none exists."""
    for offset in range(len(rows) - 1, -1, -1):
        row = rows[offset]
        if row and normalize_text(row[0]):
            return first_sheet_row + offset
    return 0


def destination_chunks(start_row: int, item_count: int, chunk_size: int = 500) -> List[Tuple[int, int]]:
    """Return 1-based inclusive destination row ranges."""
    if start_row <= 0 or item_count < 0:
        raise KeywordWorkflowError("Destination coordinates are invalid")
    if chunk_size <= 0:
        raise KeywordWorkflowError("Chunk size must be positive")
    result: List[Tuple[int, int]] = []
    remaining = item_count
    current = start_row
    while remaining:
        size = min(chunk_size, remaining)
        result.append((current, current + size - 1))
        current += size
        remaining -= size
    return result


def rows_to_append(current_row_count: int, required_last_row: int) -> int:
    if current_row_count < 0 or required_last_row < 0:
        raise KeywordWorkflowError("Row counts cannot be negative")
    return max(0, required_last_row - current_row_count)


def write_json(payload: Dict[str, Any], output: Optional[Path]) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if output is None:
        sys.stdout.write(rendered)
        return
    output.write_text(rendered, encoding="utf-8")


def write_filtered_ads_csv(
    table: Dict[str, Any], filtered_rows: Sequence[Sequence[str]], output: Path
) -> None:
    """Write a filtered, Excel-compatible CSV with all source columns intact."""
    if output.suffix.casefold() != ".csv":
        raise KeywordWorkflowError("Detailed export output must use a .csv extension")
    if output.exists():
        raise KeywordWorkflowError("Detailed export output already exists; choose a new path")
    headers = table.get("headers")
    if not isinstance(headers, list) or not headers:
        raise KeywordWorkflowError("Detailed export requires a non-empty header row")
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(table.get("preamble_rows", []))
        writer.writerow(headers)
        writer.writerows(filtered_rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    domain_parser = subparsers.add_parser("normalize-domain", help="normalize a domain or URL")
    domain_parser.add_argument("--domain", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="parse and deduplicate an Ads CSV")
    prepare_parser.add_argument("--ads-csv", required=True, type=Path)
    prepare_parser.add_argument("--seed", required=True)
    prepare_parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    prepare_parser.add_argument("--existing-file", type=Path)
    prepare_parser.add_argument("--blocked-phrase-file", type=Path)
    prepare_parser.add_argument("--buyer-intent-file", type=Path)
    prepare_parser.add_argument("--brand-file", type=Path)
    prepare_parser.add_argument(
        "--detail-output",
        type=Path,
        help="write filtered rows with every Google Ads metric column to a CSV",
    )
    prepare_parser.add_argument("--chunk-size", type=int, default=500)
    prepare_parser.add_argument("--output", type=Path)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "normalize-domain":
            sys.stdout.write(normalize_domain(args.domain) + "\n")
            return 0
        if args.detail_output and args.detail_output.resolve() == args.ads_csv.resolve():
            raise KeywordWorkflowError("Detailed export must not overwrite the source Ads CSV")
        table, csv_stats = parse_ads_csv_table(args.ads_csv)
        prepared, filtered_rows = prepare_ads_table(
            table,
            seed=args.seed,
            existing_keywords=load_existing_keywords(args.existing_file),
            chunk_size=args.chunk_size,
            language=args.language,
            blocked_phrases=(
                load_phrase_file(args.blocked_phrase_file)
                if args.blocked_phrase_file
                else None
            ),
            buyer_intent_phrases=(
                load_phrase_file(args.buyer_intent_file) if args.buyer_intent_file else None
            ),
            confirmed_brands=(load_phrase_file(args.brand_file) if args.brand_file else None),
        )
        if args.detail_output:
            write_filtered_ads_csv(table, filtered_rows, args.detail_output)
            prepared["stats"].update(
                {
                    "detail_output": str(args.detail_output.resolve()),
                    "detail_row_count": len(filtered_rows),
                    "detail_column_count": len(table["headers"]),
                }
            )
        prepared["stats"] = {**csv_stats, **prepared["stats"]}
        write_json(prepared, args.output)
        return 0
    except (KeywordWorkflowError, OSError, csv.Error) as exc:
        sys.stderr.write("error: {}\n".format(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
