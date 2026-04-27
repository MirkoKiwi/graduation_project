import time
import os

from src.generator import get_llm_references
from src.formatter import save_bibtex
from utils.helpers import ensure_ollama_is_running



def main():
    ensure_ollama_is_running()

    while True:
        user_in = input("(Type /bye to quit) Topic: ")
        if user_in.lower() == "/bye":
            break

        timestamp = int(time.time())

        print("\33[44m[*]\33[0m Generating...")
        raw_output  = get_llm_references(user_in)
        
        bib_filename = f"refs_{timestamp}.bib"
        bib_path     = save_bibtex(raw_output, bib_filename)

        print(f"\33[44m[+]\33[0m BibTeX saved at: {bib_path}")
        
        print(f"\n\33[0m--- \33[32mCOMPLETED \33[0m---")



if __name__ == "__main__":
    main()