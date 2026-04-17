import requests
import os

key = "05089677656ffea29cee6ecaec33772f"
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
models = ["claude-3-5-sonnet", "claude-3.5-sonnet", "claude-3-5-sonnet-20241022", "claude-3.5-sonnet-20241022", "claude-3.5-haiku", "claude-3-5-haiku", "claude-haiku-4.5", "gemini-3-pro", "gemini-1.5-pro", "gemini-3.1-pro"]
endpoints = ["v1/chat/completions", "v1/messages"]

payload = {
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 10
}
anthropic_payload = {
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 10,
    "model": "claude-3-5-sonnet-20241022"
}

for m in models:
    for e in endpoints:
        url = f"https://api.kie.ai/{m}/{e}"
        # try openai format
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code not in (404, 422):
            print(f"SUCCESS OPENAI {url}: {resp.status_code} {resp.text}")
        else:
            if "The page does not exist" not in resp.text and "Not Found" not in resp.text and "The model is not supported" not in resp.text:
                print(f"FAILED OPENAI {url}: {resp.status_code} {resp.text}")
        
        # try anthropic format
        headers["anthropic-version"] = "2023-06-01"
        resp = requests.post(url, headers=headers, json=anthropic_payload)
        if resp.status_code not in (404, 422):
            print(f"SUCCESS ANTHROPIC {url}: {resp.status_code} {resp.text}")
        else:
            if "The page does not exist" not in resp.text and "Not Found" not in resp.text and "The model is not supported" not in resp.text:
                print(f"FAILED ANTHROPIC {url}: {resp.status_code} {resp.text}")
        del headers["anthropic-version"]

