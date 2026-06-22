import os
from ollama import Client

from config import settings
from src.vector_db import VectorDB



def get_llm_response(input_query):
    client = Client(host=settings.ollama_api_host)

    prompt = f"""
    You're an assistant in research.
    Cite any real academic studies, in bibtex format, about: {input_query}
    """

    try:
        response = client.chat(
            model    = settings.model_name,
            messages = [{'role': 'user', 
                       'content': prompt
                    }]
        )
        return response['message']['content']
    except Exception as e:
        return f"Error: {e}"



vec_db = VectorDB()

def get_llm_rag(input_query):
    client = Client(host=settings.ollama_api_host)

    # Retrieval
    context = vec_db.query_context(input_query)

    print(f"[DEBUG] Context found: {context}")

    instruction_prompt = f"""
    You're an assistant in research.
    Use ONLY and EXCLUSIVELY documents given in the CONTEXT under here to answer the USER REQUEST.
    If the context doesn't contain anything related, answer saying that you didn't find any existing source.

    CONTEXT:
    {context}

    USER REQUEST:
    Cite any real academic studies, in bibtex format, about: {input_query}
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