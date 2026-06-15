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



def parse_bibtex_to_references(bib_content: str) -> list[Reference]:
    references = []
    # Add parsing logic
    return references





def verify_bibtex_string(raw_output: str) -> list:
    refs = parse_bibtex_to_references(raw_output)
    return verify_references(refs)