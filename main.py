import time
import os

from src.generator import get_llm_response, get_llm_rag
from src.formatter import save_bibtex
from utils.helpers import ollama_check



def main():
    ollama_check()

    while True:
        user_in = input(">>>> User:\n'/rag <prompt>' to enable RAG, '<prompt>' for raw prompt, '/bye' to quit\nTopic: ")
        

        if user_in.lower() == "/bye":
            break
        if not user_in:
            continue


        rag_enabled = False
        prompt = user_in
        suffix = "_norag"

        if user_in.lower().startswith("/rag "):
            rag_enabled = True
            prompt      = user_in[5:].strip()
            suffix      = "_rag"
            print(f"\33[45m[*]\33[0m RAG")
        else:
            prompt      = user_in
            print(f"\33[44m[*]\33[0m NO RAG")

        print("\33[44m[*]\33[0m Generating...")
        

        if rag_enabled:
            raw_output = get_llm_rag(prompt)
        else:
            raw_output = get_llm_response(prompt)
        
        print(f">>>> Model:\n{raw_output}")
        
        timestamp    = int(time.time())
        bib_filename = f"refs_{timestamp}{suffix}.bib"
        bib_path     = save_bibtex(raw_output, bib_filename)

        print(f"\33[44m[+]\33[0m BibTeX saved at: {bib_path}")
        print(f"\n\33[0m--- \33[32mCOMPLETED \33[0m---")



if __name__ == "__main__":
    main()