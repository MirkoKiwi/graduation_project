import re
import sys

from pathlib import Path
import bibtexparser
from hallucinator import Reference, Validator, ValidatorConfig, PdfExtractor, ProgressEvent


from config import config




def _verify_references(references: list[Reference]) -> list:
    if not references:
        return []

    val_config = ValidatorConfig()
    validator  = Validator(val_config)

    current_progress = _track_progress()
    
    try:
        results = validator.check(references, progress=current_progress)
        return results

    except Exception as e:
        print(f"\33[31m[!] Error validating: {e}\33[0m")
        return []



def _track_progress():
    def on_progress(event):
        if event.event_type == "checking":
            ref_title = event.title
            print(f"  \33[34m[Checking]...\33[0m [{event.index + 1}/{event.total}] {ref_title}\033[K", end="\r")
        elif event.event_type == "result":
            r = event.result
            ref_title = r.title
            icon = {
                "verified":  "\33[32m[OK - Verified]\33[0m",
                "not_found": "\33[31m[?? - Hallucinated]\33[0m",
                "mismatch":  "\33[33m[~~ - Mismatch]\33[0m"
            }.get(r.status, "[?]")
            
            source = f" ({r.source})" if r.source else ""
            print(f"\r  {icon} {r.title} {source}\033[K")

    return on_progress



def _parse_bibtex_to_references(generated_bibs: str) -> list[Reference]:
    references = []
    
    try:
        if "@" in generated_bibs:

            # TODO: the LLM often produces bibtex references without closing the final curly braces
            #       this results in bibtexparser being unable to actually parse the entire ref

            bib_db = bibtexparser.loads(generated_bibs)

            for entry in bib_db.entries:
                
                #print(f"Current ref: {index}/{total_entries}", end="\r")

                if isinstance(entry, tuple):
                    entry = next((x for x in entry if isinstance(x, dict)), None)

                if not entry or not isinstance(entry, dict):
                    continue    


                title = entry.get("title")
                if not title:
                    continue
                
                title = _clean_bibtex_field(title)
                
                # Parse authors
                author_str = entry.get("author", "")
                authors = []
                if author_str:
                    author_str = _clean_bibtex_field(author_str)
                    authors = [a.strip() for a in author_str.split(" and ")]
                
                doi      = _clean_bibtex_field(entry.get("doi", ""))
                arxiv_id = _clean_bibtex_field(entry.get("eprint", "") or entry.get("arxiv", ""))
                
                references.append(Reference(title=title, authors=authors, doi=doi, arxiv_id=arxiv_id))

    except Exception as e:
        print(f"\33[33m[!] Parsing fail ({e})\33[0m")

    return references



def _clean_bibtex_field(bib_field: str) -> str:
    if not bib_field:
        return ""
    
    # Remove curly braces
    cleaned_bib = re.sub(r'[{}]', '', bib_field)
    
    # Remove escape backslashes
    cleaned_bib = re.sub(r'\\([\'"_\-&%#])', r'\1', cleaned_bib)

    return cleaned_bib.strip()






def verify_bibtex_string(generated_references: str) -> list:
    if "@" not in generated_references or "I did not find any" in generated_references:
        print("[!] No valid references found!")
        return []
    
    refs = _parse_bibtex_to_references(generated_references)

    if not refs:
        print("[!] No valid references parsed!")
        return []
    
    return _verify_references(refs)



def print_hallucinator_stats(results) -> str:
    stats = Validator.stats(results)
    print(f"Total:           {stats.total}")
    print(f"Verified:        {stats.verified}")
    print(f"Not found:       {stats.not_found}")
    print(f"Author mismatch: {stats.author_mismatch}")
    print(f"Retracted:       {stats.retracted}")
    print(f"Skipped:         {stats.skipped}")