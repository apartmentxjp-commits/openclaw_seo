import requests
import json
import re
import logging

OLLAMA_URL = "http://localhost:11434/api/generate"

def call_qwen_json(system_prompt, user_prompt, model="qwen2.5:32b", retries=2):
    payload = {
        "model": model,
        "prompt": f"{system_prompt}\n\n{user_prompt}\n\nOutput only a raw JSON object.",
        "stream": False,
        "format": "json"
    }
    
    for attempt in range(retries + 1):
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            response.raise_for_status()
            raw_text = response.json().get("response", "").strip()
            
            # 1. Remove code fences
            clean_text = re.sub(r'```json\s*|\s*```', '', raw_text)
            
            # 2. Extract content between {}
            match = re.search(r'(\{.*\})', clean_text, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                json_str = clean_text
                
            return json.loads(json_str)
            
        except (json.JSONDecodeError, requests.RequestException) as e:
            logging.warning(f"Ollama JSON parse failed (Attempt {attempt+1}): {e}")
            if attempt == retries:
                logging.error("Max retries reached for Ollama JSON.")
                return {"error": "JSON parse failed"}
            continue

def ollama_generate(system, user, model="qwen2.5:32b"):
    payload = {
        "model": model,
        "prompt": f"{system}\n\n{user}",
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        return response.json().get("response", "")
    except Exception as e:
        return f"Ollama Error: {e}"
