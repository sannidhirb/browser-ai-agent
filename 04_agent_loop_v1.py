import os
import json
from dotenv import load_dotenv
from groq import Groq
from playwright.sync_api import sync_playwright

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def get_page_summary(page):
    page.evaluate("""
        () => {
            const els = document.querySelectorAll('input, button, a');
            let counter = 0;
            els.forEach((el) => {
                const rect = el.getBoundingClientRect();
                const isVisible = rect.width > 0 && rect.height > 0 &&
                                   window.getComputedStyle(el).visibility !== 'hidden' &&
                                   window.getComputedStyle(el).display !== 'none';
                if (isVisible) {
                    el.setAttribute('data-agent-id', counter);
                    counter++;
                }
            });
        }
    """)

    visible_text = page.inner_text("body")[:2000]

    elements = []
    tagged = page.query_selector_all("[data-agent-id]")
    for el in tagged[:20]:
        agent_id = el.get_attribute("data-agent-id")
        tag = el.evaluate("el => el.tagName.toLowerCase()")
        placeholder = el.get_attribute("placeholder") or ""
        current_value = el.input_value() if tag == "input" else ""
        text = el.inner_text()[:40] if tag != "input" else ""
        elements.append(
            f'[id={agent_id}] <{tag}> placeholder="{placeholder}" value="{current_value}" text="{text}"'
        )

    elements_text = "\n".join(elements)
    return f"VISIBLE TEXT:\n{visible_text}\n\nINTERACTIVE ELEMENTS (use the [id=N] number as the id):\n{elements_text}"


def ask_ai(task, page_summary, history):
    history_text = "\n".join(
        [f"{i+1}. {h}" for i, h in enumerate(history)]
    ) if history else "No actions taken yet."

    prompt = f"""You are a browser automation agent controlling a real browser step by step.

Task: {task}

Actions already taken so far:
{history_text}

Current page:
{page_summary}

FIRST: carefully check if the VISIBLE TEXT above already contains the answer to the task.
If it does, respond with "done" and put the answer directly from that text — do NOT try to click
anything just to "confirm" it further.

Only if the answer is genuinely not visible yet, choose ONE of these actions:
- "navigate": go to a URL. Include "value".
- "fill": type into an input. Include "id" and "value".
- "press": press a key on an element. Include "id" and "value" (e.g. "Enter").
- "click": click an element. Include "id".
- "done": task is complete. Include "answer".

Important: use the exact [id=N] number shown next to each element as "id". Do not invent CSS selectors.
Only use IDs that appear in the list above. If a field's value already matches what you need, do NOT
fill it again. Look at "Actions already taken" so you don't repeat the same action or retry a failed
element ID again.

Respond ONLY with valid JSON, no other text:
{{"action": "...", "id": "...", "value": "...", "answer": "...", "reasoning": "..."}}
Leave unused fields as null.
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(response.choices[0].message.content)


def run_agent(task, start_url, max_steps=10):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_default_timeout(5000)
        page.goto(start_url)

        history = []

        for step in range(max_steps):
            print(f"\n=== Step {step + 1} ===")
            summary = get_page_summary(page)
            decision = ask_ai(task, summary, history)
            print("AI decided:", decision["action"], "-", decision.get("reasoning"))

            action = decision["action"]

            try:
                if action == "done":
                    print("\n✅ TASK COMPLETE")
                    print("Answer:", decision["answer"])
                    break

                elif action == "navigate":
                    page.goto(decision["value"])
                    history.append(f'navigated to {decision["value"]}')

                elif action == "fill":
                    sel = f'[data-agent-id="{decision["id"]}"]'
                    page.fill(sel, decision["value"])
                    history.append(f'filled element {decision["id"]} with "{decision["value"]}"')

                elif action == "press":
                    sel = f'[data-agent-id="{decision["id"]}"]'
                    page.press(sel, decision["value"])
                    history.append(f'pressed {decision["value"]} on element {decision["id"]}')

                elif action == "click":
                    sel = f'[data-agent-id="{decision["id"]}"]'
                    page.click(sel)
                    history.append(f'clicked element {decision["id"]}')

            except Exception as e:
                print(f"⚠️ Action failed: {e}")
                history.append(f'{action} on element {decision.get("id")} FAILED - do not retry this exact id, try something else')

            page.wait_for_timeout(1500)
        else:
            print("\n⚠️ Max steps reached without finishing.")

        page.screenshot(path="agent_result.png")
        browser.close()


if __name__ == "__main__":
    run_agent(
        task="Search for 'python jobs bangalore' and tell me the title of the first result",
        start_url="https://duckduckgo.com"
    )