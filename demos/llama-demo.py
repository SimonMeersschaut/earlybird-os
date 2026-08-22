import requests

with open("llm-prompt.txt", 'r') as f:
    prompt = f.read()

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "llama3.2:1b",
        "prompt": prompt,
        "stream": False,
    },
)

print("Running llama model")
summary = response.json()["response"]
print(summary)