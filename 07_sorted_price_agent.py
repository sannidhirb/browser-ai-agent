import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from playwright.sync_api import sync_playwright

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def get_page_summary(page, max_elements=25):
    """Reads the page, tags visible interactive elements, and scores them so that
    sort/filter controls and price-like text are prioritized over navigation noise."""
    page.evaluate("""
        () => {
            const els = document.querySelectorAll('input, button, a, select, textarea');
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

    visible_text = page.inner_text("body")[:2500]

    elements = []
    tagged = page.query_selector_all("[data-agent-id]")

    scored_elements = []
    sort_keywords = ["low to high", "high to low", "price", "sort"]

    for el in tagged:
        agent_id = el.get_attribute("data-agent-id")
        tag = el.evaluate("el => el.tagName.toLowerCase()")
        placeholder = el.get_attribute("placeholder") or ""
        current_value = ""
        if tag in ("input", "textarea"):
            try:
                current_value = el.input_value()
            except Exception:
                current_value = ""
        text = el.inner_text()[:60] if tag not in ("input", "textarea") else ""

        score = 0
        text_lower = text.lower()
        if any(kw in text_lower for kw in sort_keywords):
            score += 20
        if re.search(r"[\u20b9$]\s?\d", text):
            score += 10
        if tag == "input":
            score += 5
        if len(text) > 15:
            score += 2

        scored_elements.append((score, agent_id, tag, placeholder, current_value, text))

    scored_elements.sort(key=lambda x: x[0], reverse=True)

    for score, agent_id, tag, placeholder, current_value, text in scored_elements[:max_elements]:
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

IMPORTANT RULE FOR "CHEAPEST" / "MOST EXPENSIVE" / PRICE COMPARISON TASKS:
Do NOT conclude "done" just because you see one item with a price. Search results are often sorted
by relevance, not price. If a "Price -- Low to High" or similar sort control is visible, click it
FIRST before reading results, unless you have already done so according to "Actions already taken".
Only conclude "done" once results are sorted by price, or you have compared at least 3-4 visible
items yourself and are confident you have the true minimum/maximum.

FIRST: check if the VISIBLE TEXT above already contains a reliable answer to the task, following the
rule above. If it does, respond with "done" and give the answer directly.

Only if the answer is genuinely not ready yet, choose ONE of these actions:
- "navigate": go to a URL. Include "value".
- "fill": type into an input. Include "id" and "value".
- "press": press a key on an element. Include "id" and "value" (e.g. "Enter").
- "click": click an element using its numbered id. Include "id".
- "click_by_text": click any element containing specific visible text, even if it has no [id=N]
  (useful for sort links, tabs, or buttons not in the interactive elements list). Include "value"
  with the exact or partial visible text to click, e.g. "Low to High".
- "done": task is complete. Include "answer".

Important: use the exact [id=N] number shown next to each element as "id" for the "click" action.
Do not invent CSS selectors. Only use IDs that appear in the list above. Do NOT fill a field that
already has the right value. Look at "Actions already taken" so you don't repeat the same action or
retry a failed element/action again. If you see a popup, login prompt, or overlay blocking the page,
close it first (by id if listed, or click_by_text if not).

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
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_folder = f"reports/{run_id}"
    os.makedirs(run_folder, exist_ok=True)

    report = {"task": task, "start_url": start_url, "timestamp": run_id,
              "steps": [], "final_answer": None, "status": "incomplete"}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_default_timeout(5000)
        page.goto(start_url, timeout=30000, wait_until="domcontentloaded")

        history = []

        for step in range(max_steps):
            print(f"\n=== Step {step + 1} ===")
            summary = get_page_summary(page)
            decision = ask_ai(task, summary, history)
            print("AI decided:", decision["action"], "-", decision.get("reasoning"))

            action = decision["action"]
            step_screenshot = f"{run_folder}/step_{step + 1}.png"
            step_record = {"step": step + 1, "action": action,
                            "reasoning": decision.get("reasoning"), "screenshot": step_screenshot}

            if action == "done":
                report["final_answer"] = decision["answer"]
                report["status"] = "success"
                page.screenshot(path=step_screenshot)
                report["steps"].append(step_record)
                print("\n✅ TASK COMPLETE")
                print("Answer:", decision["answer"])
                break

            try:
                if action == "navigate":
                    page.goto(decision["value"], timeout=30000, wait_until="domcontentloaded")
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

                elif action == "click_by_text":
                    page.get_by_text(decision["value"], exact=False).first.click(timeout=5000)
                    history.append(f'clicked element containing text "{decision["value"]}"')

            except Exception as e:
                print(f"⚠️ Action failed: {e}")
                history.append(f'{action} FAILED ({decision.get("id") or decision.get("value")}) - try something else')
                step_record["error"] = str(e)

            page.screenshot(path=step_screenshot)
            report["steps"].append(step_record)
            page.wait_for_timeout(1500)
        else:
            report["status"] = "max_steps_reached"
            print("\n⚠️ Max steps reached without finishing.")

        browser.close()

    with open(f"{run_folder}/report.json", "w") as f:
        json.dump(report, f, indent=2)

    with open(f"{run_folder}/report.md", "w", encoding="utf-8") as f:
        f.write(f"# Task Report\n\n**Task:** {task}\n\n**Status:** {report['status']}\n\n")
        f.write(f"**Final Answer:** {report['final_answer']}\n\n## Steps\n\n")
        for s in report["steps"]:
            f.write(f"### Step {s['step']}: {s['action']}\n- Reasoning: {s.get('reasoning')}\n")
            f.write(f"- Screenshot: {s['screenshot']}\n")
            if "error" in s:
                f.write(f"- ⚠️ Error: {s['error']}\n")
            f.write("\n")

    print(f"\n📁 Full report saved to: {run_folder}/report.md")
    return report


if __name__ == "__main__":
    run_agent(
        task="Find the price of the cheapest iPhone listed on this page",
        start_url="https://www.flipkart.com/search?q=iphone"
    )