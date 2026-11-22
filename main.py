import time
import argparse

from src.generator import get_llm_response, get_llm_rag
from src.formatter import save_bibtex
from utils.helpers import ollama_check
from evaluation.hallucinator_eval import verify_bibtex_string, print_hallucinator_stats



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["norag", "rag_title_only", "rag_title_abstract"],
        default="norag",
        help="--prompt starts model generation mode"
    )
    parser.add_argument("--k", type=int, default=5, help="k-citations")
    parser.add_argument("--prompt", type=str, default=None)
    args = parser.parse_args()

    if args.k <= 0:
        print("\33[31m[!]\33[0m --k must be > 0")
        return
    
    ollama_check()

    if args.prompt is not None:
        prompt = args.prompt.strip()
        if not prompt:
            print("\33[31m[!]\33[0m Empty prompt")
            return
        run_model(prompt, mode=args.mode, k_citations=args.k)
        return

    k_citations = args.k


    while True:
        user_in = input(
            f"\n>>>> User (k={k_citations}):\n"
            "  <prompt>            -> raw prompt (no RAG)\n"
            "  /rag <prompt>       -> RAG (title_only)\n"
            "  /rag_abs <prompt>   -> RAG (title_abstract)\n"
            "  /k <num>            -> set k_citations\n"
            "  /bye                -> quit\n"
            "Topic: "
        )

        action, payload = _sanitize_user_in(user_in)

        if action == "bye":
            break
        if action == "set_k":
            if payload.isdigit() and int(payload) > 0:
                k_citations = int(payload)
                print(f"\33[32m[*]\33[0m k_citations = {k_citations}")
            else:
                print("\33[33m[!]\33[0m Usage: /k <positive_integer>")
            continue
        if action == "unknown":
            print(f"\33[33m[!]\33[0m Unknown command: {payload}")
            continue
        if not payload:
            print("\33[33m[!]\33[0m Empty prompt.")
            continue

        run_model(payload, mode=action, k_citations=k_citations)



# =========================================================================


_MODE = {
    "norag": "_norag",
    "rag_title_only": "_rag_title",
    "rag_title_abstract": "_rag_abstract",
}


def run_model(prompt: str, mode: str, k_citations: int) -> None:
    if mode == "norag":
        print(f"\33[34m[*] NO RAG | k={k_citations}\33[0m")
        print("\33[34m[*] \33[0mGenerating...")
        raw_output = get_llm_response(prompt, k_citations=k_citations)
    else:
        print(f"\33[35m[*] RAG ({mode}) | k={k_citations}\33[0m")
        print("\33[34m[*] \33[0mGenerating...")
        raw_output = get_llm_rag(prompt, mode=mode, k_citations=k_citations)

    print(f">>>> Model:\n{raw_output}")

    if raw_output.startswith("Error:"):
        print("\33[31m[!]\33[0m Generation failed, skipping evaluation.")
        return

    timestamp = int(time.time())
    suffix = _MODE[mode]
    bib_filename = f"refs_{timestamp}{suffix}.bib"
    bib_path = save_bibtex(raw_output, bib_filename)

    print(f"\33[44m[+]\33[0m BibTeX saved at: {bib_path}")
    print("\n\33[0m--- \33[32mCOMPLETED \33[0m---")

    print("\33[0m--- HALLUCINATOR ANALYSIS \33[0m---\n")
    hallucinator_report = verify_bibtex_string(raw_output)

    if hallucinator_report:
        verified = sum(1 for r in hallucinator_report if r.status == "verified")
        print(f"  └─ Control done. Legitimate refs: {verified}/{len(hallucinator_report)}")

    print("\n\33[0m--- \33[32mCOMPLETED \33[0m---")
    print(print_hallucinator_stats(hallucinator_report))



def _sanitize_user_in(raw: str) -> tuple[str, str]:
    text = raw.strip()
    text_lower = text.lower()

    if text_lower == "/bye":
        return "bye", ""

    if text_lower == "/k" or (text_lower.startswith("/k") and text_lower[2].isspace()):
        return "set_k", text[2:].strip()

    for prefix, mode in (
        ("/rag_title_abstract", "rag_title_abstract"),
        ("/rag_abs", "rag_title_abstract"),
        ("/rag-abs", "rag_title_abstract"),
        ("/rag_title_only", "rag_title_only"),
        ("/rag", "rag_title_only"),
    ):
        if text_lower == prefix or (text_lower.startswith(prefix) and text_lower[len(prefix)].isspace()):
            return mode, text[len(prefix):].strip()

    if text.startswith("/"):
        return "unknown", text

    return "norag", text


# =========================================================================



if __name__ == "__main__":
    main()