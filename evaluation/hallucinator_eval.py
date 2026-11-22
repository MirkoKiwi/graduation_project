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

_BIB_START = re.compile(
    r"@(?!string\b|comment\b|preamble\b)[a-zA-Z]+\s*[{(]",
    re.IGNORECASE,
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
            print(f"  \33[34m[Checking]...\33[0m [{event.index + 1}/{event.total}] {event.title}\033[K", end="\r")
        elif event.event_type == "result":
            r = event.result
            icon = {
                "verified":        "\33[32m[OK - Verified]\33[0m",
                "not_found":       "\33[31m[?? - Hallucinated]\33[0m",
                "mismatch":        "\33[33m[~~ - Mismatch]\33[0m",
                "author_mismatch": "\33[33m[~~ - Mismatch]\33[0m",
                "retracted":       "\33[31m[XX - Retracted]\33[0m",
            }.get(r.status, f"[{r.status}]")

            source = f" ({r.source})" if r.source else ""
            print(f"\r  {icon} {r.title}{source}\033[K")

    return on_progress



def _fix_bibtex_chunk(raw: str) -> list[str]:
    cleaned = re.sub(r"```[a-zA-Z]*\s*", "", raw)
    matches = list(_BIB_START.finditer(cleaned))
    if not matches:
        return []

    fixed = []
    for idx, m in enumerate(matches):
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(cleaned)
        chunk = cleaned[start:end].strip()

        open_ch = m.group(0)[-1]
        close_ch = "}" if open_ch == "{" else ")"
        open_idx = m.end() - m.start() - 1

        depth = 0
        close_pos = -1
        escaped = False
        for i in range(open_idx, len(chunk)):
            ch = chunk[i]
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    close_pos = i
                    break

        if close_pos != -1:
            chunk = chunk[: close_pos + 1]
        elif depth > 0:
            chunk = chunk.rstrip(", \n\t") + (close_ch * depth)

        if chunk:
            fixed.append(chunk)

    return fixed



def _parse_chunk_entries(chunk: str) -> list[dict]:
    # bibtexparser v2.x
    if hasattr(bibtexparser, "parse_string"):
        lib = bibtexparser.parse_string(chunk)
        blocks = list(getattr(lib, "entries", []))

        for fb in getattr(lib, "failed_blocks", []):
            recovered = getattr(fb, "ignore_error_block", None)
            if recovered is not None and hasattr(recovered, "fields"):
                blocks.append(recovered)

        parsed = []
        for entry in blocks:
            fields = getattr(entry, "fields", None)
            if fields is not None:
                parsed.append({f.key.lower(): f.value for f in fields if f.value})
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
    normalized = re.sub(r"\s+", " ", normalized).strip(" ,;")
    if not normalized:
        return []

    if re.search(r"\band\b", normalized, flags=re.IGNORECASE):
        parts = [a.strip(" ,;") for a in re.split(r"\s+\band\b\s+", normalized, flags=re.IGNORECASE)]
    elif "," in normalized:
        parts = [p.strip() for p in normalized.split(",") if p.strip()]
        is_particle = bool(parts and re.match(r"^(?:van|von|de|del|della|di|da|la|le)\b", parts[0], re.I))
        if len(parts) >= 3 and all(len(p.split()) >= 2 for p in parts):
            pass
        elif len(parts) == 2 and not is_particle and all(len(p.split()) >= 2 for p in parts):
            pass
        else:
            parts = [normalized]
    else:
        parts = [normalized]

    return [p for p in parts if p and p.lower() not in {"others", "et al", "et al."}]



def _clean_bibtex_field(bib_field: str) -> str:
    if not bib_field:
        return ""

    cleaned = re.sub(r'\\(["\'`^~=.Hcvukrdtb])\s*\{([a-zA-Z])\}', r'\2', bib_field)
    cleaned = re.sub(r'\\(["\'`^~=.])\s*([a-zA-Z])', r'\2', cleaned)
    cleaned = re.sub(r"[{}]", "", cleaned)
    cleaned = re.sub(r"\\(['\"_\-&%#])", r"\1", cleaned)

    return re.sub(r"\s+", " ", cleaned).strip()



def _regex_fallback(chunk: str) -> dict | None:
    def _grab(field: str) -> str:
        m = re.search(rf'\b{field}\s*=\s*', chunk, flags=re.IGNORECASE)
        if not m:
            return ""
        i = m.end()
        n = len(chunk)
        while i < n and chunk[i].isspace():
            i += 1
        if i >= n:
            return ""

        if chunk[i] == "{":
            depth = 0
            start = i + 1
            escaped = False
            for j in range(i, n):
                ch = chunk[j]
                if escaped:
                    escaped = False
                    continue
                if ch == "\\":
                    escaped = True
                    continue
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return chunk[start:j].strip()
            return chunk[start:].strip()

        if chunk[i] == '"':
            start = i + 1
            escaped = False
            for j in range(start, n):
                ch = chunk[j]
                if escaped:
                    escaped = False
                    continue
                if ch == "\\":
                    escaped = True
                    continue
                if ch == '"':
                    return chunk[start:j].strip()
            return chunk[start:].strip()

        m_bare = re.match(r"([^,\n}]+)", chunk[i:])
        return m_bare.group(1).strip() if m_bare else ""

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
    if "@" not in generated_references:
        if any(r in low for r in _CONST_REFUSAL):
            print("[!] Model refused (no sources found).")
        else:
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
        return "No references evaluated."

    stats = Validator.stats(results)
    return (
        f"Total:           {stats.total}\n"
        f"Verified:        {stats.verified}\n"
        f"Not found:       {stats.not_found}\n"
        f"Author mismatch: {stats.author_mismatch}\n"
        f"Retracted:       {stats.retracted}\n"
        f"Skipped:         {stats.skipped}"
    )