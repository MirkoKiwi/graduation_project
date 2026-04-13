import os
from ollama import Client
from config import settings



def get_llm_references(user_in):
    client = Client(host=settings.ollama_host)

    prompt = f"Cite 5 real academic studies about: {user_in}"

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