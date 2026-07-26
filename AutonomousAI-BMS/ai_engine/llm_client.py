import requests
import json


OLLAMA_URL = "http://localhost:11434/api/generate"

MODEL = "qwen2.5:3b"


def ask_llm(prompt):

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1
        }
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        llm_text = data["response"]

        return json.loads(llm_text)

    except Exception as error:

        print(
            f"[LLM ERROR] {error}"
        )

        return None