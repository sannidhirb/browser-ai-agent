import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

task = "Find the cheapest iPhone"
page_content = "Search results: iPhone 15 - $799, iPhone 14 - $699, iPhone SE - $429"

prompt = f"""You are a browser automation agent. You control a web browser step by step to complete a task.

Task: {task}
Current page content: {page_content}

You must choose exactly ONE of these actions:
- "navigate": go to a URL. Include "value" with the URL.
- "fill": type text into an input field. Include "selector" and "value".
- "click": click an element. Include "selector".
- "wait": wait for the page to load more content.
- "done": the task is already complete based on what you can see. Include "answer" with the final result.

Respond ONLY with valid JSON, nothing else, in this exact format:
{{"action": "...", "selector": "...", "value": "...", "answer": "...", "reasoning": "..."}}

Leave any fields that don't apply as null.
"""

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": prompt}]
)

raw_text = response.choices[0].message.content
print("Raw response:\n", raw_text)

decision = json.loads(raw_text)
print("\nAction chosen:", decision["action"])
print("Answer:", decision.get("answer"))
print("Reasoning:", decision.get("reasoning"))