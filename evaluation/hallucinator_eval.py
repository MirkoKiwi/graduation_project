import re
import sys

from pathlib import Path
import bibtexparser
from hallucinator import Reference, Validator, ValidatorConfig, PdfExtractor


from config import config





def verify_references(references: list[Reference]) -> list:
    if not references:
        return []

    val_config = ValidatorConfig()
    validator = Validator(val_config)
    
    try:
        results = validator.check(references)
        return results
    
    except Exception as e:
        print(f"\33[31m[!] Error validating: {e}\33[0m")
        return []



def parse_bibtex_to_references(generated_bibs: str) -> list[Reference]:
    references = []
    
    try:
        if "@" in generated_bibs:
            bib_db = bibtexparser.loads(generated_bibs)
            for entry in bib_db.entries:
                title = entry.get("title")
                if not title:
                    continue
                
                title = clean_bibtex_field(title)
                
                # Parse authors
                author_str = entry.get("author", "")
                authors = []
                if author_str:
                    author_str = clean_bibtex_field(author_str)
                    authors = [a.strip() for a in author_str.split(" and ")]
                
                doi      = clean_bibtex_field(entry.get("doi", ""))
                arxiv_id = clean_bibtex_field(entry.get("eprint", "") or entry.get("arxiv", ""))
                
                references.append(Reference(title=title, authors=authors, doi=doi, arxiv_id=arxiv_id))

    except Exception as e:
        print(f"\33[33m[!] Parsing fail ({e})\33[0m")

    return references



def clean_bibtex_field(bib_field: str) -> str:
    if not bib_field:
        return ""
    
    # Remove curly braces
    cleaned_bib = re.sub(r'[{}]', '', bib_field)
    
    # Remove escape backslashes
    cleaned_bib = re.sub(r'\\([\'"_\-&%#])', r'\1', cleaned_bib)

    return cleaned_bib.strip()






def verify_bibtex_string(raw_output: str) -> list:
    refs = parse_bibtex_to_references(raw_output)
    return verify_references(refs)