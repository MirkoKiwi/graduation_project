import subprocess
import requests
import time
import re

from config import settings


def ensure_ollama_is_running():
    import os

    host = settings.ollama_api_host
    print(f"OLLAMA Host:   {host}")
    print(f"Current Model: {settings.model_name}")
    
    try:
        requests.get(f"{host}/api/tags", timeout=3)
        print(f"\33[42m[*]\33[0m Ollama connected on {host}")
    except Exception as e:
        print(f"\33[41m[!]\33[0m Error, unreachable on {host}")
        print(f"Error {e}")
        exit(1)