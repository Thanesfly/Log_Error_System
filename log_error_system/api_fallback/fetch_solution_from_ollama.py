import subprocess
import json

def fetch_solution_from_ollama(message):
    try:
        prompt = f"You are a bank IT support assistant. The log error is: '{message}'. Suggest a short, clear fix."
        result = subprocess.run(
            ["ollama", "run", "llama3", prompt],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"⚠️ Ollama Error: {e}"
