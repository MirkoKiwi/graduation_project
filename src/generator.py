import os
from ollama import Client

from config import settings
from src.vector_db import VectorDB




_COLLECTION_MODES = {
    "rag_title_only": "acl_title_only",
    "rag_title_abstract": "acl_title_abstract",
}


_VEC_DB_CACHE: dict[str, VectorDB] = {}



def _get_vec_db(mode: str) -> VectorDB:
    if mode not in _COLLECTION_MODES:
        raise ValueError(f"Invalid RAG mode '{mode}'. Choices: {list(_COLLECTION_MODES)}")

    collection_name = _COLLECTION_MODES[mode]
    if collection_name not in _VEC_DB_CACHE:
        _VEC_DB_CACHE[collection_name] = VectorDB(collection_name=collection_name)

    return _VEC_DB_CACHE[collection_name]



def get_llm_response(input_query: str, k_citations: int = 5) -> str:
    client = Client(host=settings.ollama_api_host)

    prompt = f"""You are an academic research assistant.
    Write a short academic paragraph about the topic below citing exactly {k_citations} real academic studies using [citekey] notation, followed by their BibTeX entries.

    TOPIC: {input_query}

    OUTPUT FORMAT (follow strictly):
    PARAGRAPH:
    <academic paragraph with inline [citekey] citations>

    BIBTEX:
    ```bibtex
    <exact {k_citations} BibTeX entries matching the [citekey]s cited above>
    ```
    """

    try:
        response = client.chat(
            model=settings.model_name,
            messages=[{'role': 'user', 'content': prompt}]
        )
        return response['message']['content']
    except Exception as e:
        return f"Error: {e}"



def get_llm_rag(input_query: str, mode: str = "rag_title_only", k_citations: int = 5) -> str:
    client = Client(host=settings.ollama_api_host)
    vec_db = _get_vec_db(mode)

    # Retrieval
    n_results = max(5, k_citations + 2)
    context = vec_db.query_context(input_query, n_results=n_results)

    print(f"[DEBUG] Context found: {context}\nMode: {mode} | n_results: {n_results} | Context length: {len(context)}")

    if not context.strip():
        return "I did not find any existing source"


    instruction_prompt = f"""
    You are an academic research assistant.
    Use ONLY and EXCLUSIVELY the studies provided in CONTEXT below.
    Do NOT invent, modify, or extrapolate titles, authors, years, URLs, or DOIs.
    If the CONTEXT does not contain studies directly relevant to the TOPIC, answer EXACTLY with:
    I did not find any existing source

    CONTEXT:
    {context}

    TOPIC: {input_query}

    TASK:
    Write a short academic paragraph about the TOPIC citing up to {k_citations} relevant studies from CONTEXT using [citekey] notation, followed by their exact BibTeX entries from CONTEXT.
    
    OUTPUT FORMAT (follow strictly):
    PARAGRAPH:
    <academic paragraph with inline [citekey] citations>

    BIBTEX:
    ```bibtex
    <BibTeX entries copied from CONTEXT matching the [citekey]s cited above>
    ```
    """

    print(f"[DEBUG] End of context")
    
    try:
        response = client.chat(
            model=settings.model_name,
            messages=[{'role': 'user', 'content': instruction_prompt}]
        )
        return response['message']['content']
    except Exception as e:
        return f"Error: {e}"