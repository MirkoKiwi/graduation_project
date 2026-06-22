import time
import os

from src.generator import get_llm_response, get_llm_rag
from src.formatter import save_bibtex
from utils.helpers import ollama_check
from evaluation.hallucinator_eval import verify_bibtex_string, print_hallucinator_stats



def main():
    ollama_check()

    while True:
        user_in = input(">>>> User:\n'/rag <prompt>' to enable RAG, '<prompt>' for raw prompt, '/bye' to quit\nTopic: ")
        

        if user_in.strip().lower() == "/bye":
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
            print(f"\33[35m[*] RAG\33[40m")
        else:
            prompt      = user_in
            print(f"\33[34m[*] NO RAG\33[40m")

        print("\33[34m[*] \33[0mGenerating...")
        

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

        print(f"\33[0m--- HALLUCINATOR ANALYSIS \33[0m---\n")
        hallucinator_report = verify_bibtex_string(raw_output)
        
        if hallucinator_report:
            verified = sum(1 for r in hallucinator_report if r.status == "verified")
            print(f"  └─ Control done. Legitimate refs: {verified}/{len(hallucinator_report)}")
        
        print(f"\n\33[0m--- \33[32mCOMPLETED \33[0m---")
        print(print_hallucinator_stats(hallucinator_report))

        user_in = ""




if __name__ == "__main__":
    main()