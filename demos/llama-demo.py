import requests

with open("llm-prompt.txt", 'r') as f:
    user_prompt = f.read()
    
    
# light weight model: "llama3.2:1b"
# High end: "qwen2.5:1.5b"

# Append the prefix to the prompt
prefix = "Goedemorgen Simon! Hier is je ochtendbriefing voor vandaag, zaterdag 22 augustus 2026."

response = requests.post(
    "http://localhost:11434/api/chat",
    json={
        "model": "qwen2.5:1.5b",
        "messages": [
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": prefix}
        ],
        "stream": False,
    },
)

# Ollama will complete the assistant's message from where it left off
completion = response.json()["message"]["content"]
full_output = prefix + completion

print(full_output)