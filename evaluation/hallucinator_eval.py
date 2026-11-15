import re
import sys

from collections import Counter
from collections.abc import Callable
from pathlib import Path

import bibtexparser

from hallucinator import Reference, Validator, ValidatorConfig, PdfExtractor, ProgressEvent


from config import config




_CONST_REFUSAL = (
    "i did not find any existing source",
    "no_relevant_source",
)


def _get_validator() -> Validator:
    acl_path   = config.data_dir / "acl.db"
    val_config = ValidatorConfig()

    if acl_path.exists():
        val_config.acl_offline_path = str(acl_path)
        try:
            return Validator(val_config)
        except RuntimeError as e:
            print(f"\33[33m[!] Offline ACL DB rejected ({e}), fallback to online\33[0m")

    return Validator(ValidatorConfig())



def _track_progress() -> Callable:
    def on_progress(event) -> None:
        if event.event_type == "checking":
            ref_title = event.title
            print(f"  \33[34m[Checking]...\33[0m [{event.index + 1}/{event.total}] {ref_title}\033[K", end="\r")
        elif event.event_type == "result":
            r = event.result
            ref_title = r.title
            icon = {
                "verified":        "\33[32m[OK - Verified]\33[0m",
                "not_found":       "\33[31m[?? - Hallucinated]\33[0m",
                "mismatch":        "\33[33m[~~ - Mismatch]\33[0m",
                "author_mismatch": "\33[33m[~~ - Mismatch]\33[0m",
                "retracted":       "\33[31m[XX - Retracted]\33[0m",
            }.get(r.status, f"[{r.status}]")

            source = f" ({r.source})" if r.source else ""
            kind = f" [{r.mismatch_kind}]" if getattr(r, "mismatch_kind", None) else ""
            print(f"\r  {icon} {r.title}{source}{kind}\033[K")

    return on_progress



def _fix_bibtex_chunk(raw: str) -> list[str]:
    cleaned = re.sub(r"```(?:bibtex|bib|latex)?", "", raw, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "")

    entry_pattern = r"@\s*[a-zA-Z]+\s*[{(]"
    starts = [m.start() for m in re.finditer(entry_pattern, cleaned)]
    if not starts:
        return []

    line_starts = {m.start(1) for m in re.finditer(rf"(?:^|\n)\s*({entry_pattern})", cleaned)}
    chunks = []
    prev_end = 0

    for start in starts:
        if start < prev_end:
            continue

        open_match = re.search(r"[{(]", cleaned[start:])
        if not open_match:
            continue

        open_idx = start + open_match.start()
        open_ch  = open_match.group(0)
        close_ch = "}" if open_ch == "{" else ")"
        depth    = 0
        cut_pos  = None
        stop_pos = len(cleaned)

        for i in range(open_idx, len(cleaned)):
            if i in line_starts and i > start:
                stop_pos = i
                break

            ch   = cleaned[i]
            prev = cleaned[i - 1] if i > 0 else ""
            if prev == "\\":
                continue

            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    cut_pos = i + 1
                    break

        if cut_pos is not None:
            chunk = cleaned[start:cut_pos].strip()
            prev_end = cut_pos
        else:
            chunk = cleaned[start:stop_pos].strip()
            if len(re.findall(r'(?<!\\)"', chunk)) % 2:
                chunk += '"'
            if depth > 0:
                chunk += close_ch * depth
            prev_end = stop_pos

        if chunk:
            chunks.append(chunk)

    return chunks



def _parse_chunk_entries(chunk: str) -> list[dict]:
    # bibtexparser v2.x
    if hasattr(bibtexparser, "parse_string"):
        lib = bibtexparser.parse_string(chunk)
        parsed = []
        for entry in getattr(lib, "entries", []):
            fields = getattr(entry, "fields", None)
            if fields is not None:
                parsed.append({f.key.lower(): f.value for f in fields})
        return parsed

    # bibtexparser v1.x fallback
    bib_db = bibtexparser.loads(chunk)
    return [
        {k.lower(): v for k, v in e.items()}
        for e in getattr(bib_db, "entries", [])
        if isinstance(e, dict)
    ]



def _split_authors(author: str) -> list[str]:
    if not author:
        return []

    normalized = re.sub(r",?\s*\bet\s+al\.?", "", author, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return []

    if re.search(r"\band\b", normalized, flags=re.IGNORECASE):
        parts = re.split(r"\s+\band\b\s+", normalized, flags=re.IGNORECASE)
    elif "," in normalized:
        cand = [p.strip() for p in normalized.split(",") if p.strip()]
        parts = cand if (len(cand) >= 2 and all(len(p.split()) >= 2 for p in cand)) else [normalized]
    else:
        parts = [normalized]

    return [p for p in parts if p and p.lower() not in {"others", "et al", "et al."}]



def _clean_bibtex_field(bib_field: str) -> str:
    if not bib_field:
        return ""
    
    cleaned = re.sub(r'\\(["\'`^~=.Hcvukrdtb])\s*\{([a-zA-Z])\}', r'\2', bib_field)
    cleaned = re.sub(r'\\(["\'`^~=.])\s*([a-zA-Z])', r'\2', cleaned)
    cleaned = re.sub(r'[{}]', '', cleaned)
    cleaned = re.sub(r'\\([_\-&%#])', r'\1', cleaned)

    return re.sub(r'\s+', ' ', cleaned).strip()



def _regex_fallback(chunk: str) -> dict | None:
    def _grab(field: str) -> str:
        m = re.search(
            rf'\b{field}\s*=\s*(?:\{{([^{{}}]*(?:\{{[^{{}}]*\}}[^{{}}]*)*)\}}|"([^"]*)")',
            chunk,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return (m.group(1) or m.group(2) or "").strip() if m else ""

    title = _grab("title")
    if not title:
        return None

    return {
        "title":  title,
        "author": _grab("author"),
        "doi":    _grab("doi"),
        "eprint": _grab("eprint") or _grab("arxiv"),
    }



def _verify_references(references: list[Reference], validator: Validator | None = None) -> list:
    if not references:
        return []

    validator = validator or _get_validator()
    try:
        return validator.check(references, progress=_track_progress())
    except Exception as e:
        print(f"\33[31m[!] Error validating: {e}\33[0m")
        return []


    
def verify_bibtex_string(generated_references: str, validator: Validator | None = None) -> list:
    low = generated_references.lower()
    if "@" not in generated_references or any(r in low for r in _CONST_REFUSAL):
        print("[!] No valid references found!")
        return []

    refs = _parse_bibtex_to_references(generated_references)
    if not refs:
        print("[!] No valid references parsed!")
        return []

    return _verify_references(refs, validator=validator)



def _parse_bibtex_to_references(generated_bibs: str) -> list[Reference]:
    chunks = _fix_bibtex_chunk(generated_bibs)
    if not chunks:
        return []

    references = []
    for chunk in chunks:
        entries = []
        try:
            entries = _parse_chunk_entries(chunk)
        except Exception as e:
            print(f"\33[33m[!] bibtexparser fail ({e}), trying regex fallback\33[0m")

        if not entries:
            fallback = _regex_fallback(chunk)
            if fallback:
                entries = [fallback]

        for entry in entries:
            if isinstance(entry, tuple):
                entry = next((x for x in entry if isinstance(x, dict)), None)
            if not entry or not isinstance(entry, dict):
                continue

            title = _clean_bibtex_field(entry.get("title", ""))
            if not title:
                continue

            author_str = _clean_bibtex_field(entry.get("author", ""))
            authors = _split_authors(author_str)
            doi = _clean_bibtex_field(entry.get("doi", ""))
            arxiv_id = _clean_bibtex_field(entry.get("eprint", "") or entry.get("arxiv", ""))

            references.append(
                Reference(
                    title=title,
                    authors=authors,
                    doi=doi or None,
                    arxiv_id=arxiv_id or None,
                )
            )

    return references



def print_hallucinator_stats(results) -> str:
    if not results:
        return "Total: 0"
    counts = Counter(r.status for r in results)
    mismatch = counts.get("mismatch", 0) + counts.get("author_mismatch", 0)
    return "\n".join([
        f"Total:      {len(results)}",
        f"Verified:   {counts.get('verified', 0)}",
        f"Not found:  {counts.get('not_found', 0)}",
        f"Mismatch:   {mismatch}",
        f"Retracted:  {counts.get('retracted', 0)}",
    ])