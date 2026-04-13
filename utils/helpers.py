import subprocess
import requests
import time
import re



def ensure_ollama_is_running():
    import os

    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    try:
        requests.get(f"{host}/api/tags", timeout=3)
        print(f"\33[42m[*]\33[0m Ollama connected on {host}")
    except:
        print(f"\33[41m[!]\33[0m Error, unreachable on {host}")
        exit(1)