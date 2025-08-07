import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

def fetch_solution_from_api(message):
    if not api_key:
        return "API key is missing."

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-70b-8192",  # ✅ use the supported model
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a bank IT support assistant for ATM systems. Given a log error, provide a detailed but brief fix tailored to e-Agent ATM terminals."
                    },
                    {
                        "role": "user",
                        "content": f"The log error is: {message}. Suggest a fix."
                    }
                ],
                "max_tokens": 150
            }
        )
        data = response.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"].strip()
        elif "error" in data:
            return f"⚠️ API Error: {data['error'].get('message', 'Unknown error')}"
        else:
            return "⚠️ API Error: Unexpected response structure."

    except Exception as e:
        return f"⚠️ API Error: {str(e)}"
