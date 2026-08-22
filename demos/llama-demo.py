import requests

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "llama3.2:1b",
        "prompt": "Summarize this in two short sentences for a morning voice report: Today is sunny, 22°C, and there are no calendar events.",
        "stream": False,
    },
)

print("Running llama model")
summary = response.json()["response"]
print(summary)