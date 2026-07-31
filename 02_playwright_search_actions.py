from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://duckduckgo.com")

    page.fill("input[name='q']", "highest goals in football match")
    page.press("input[name='q']", "Enter")
    page.wait_for_timeout(2000)  # give the page a moment to fully render

    titles = page.query_selector_all("[data-testid='result-title-a']")
    print(f"Found {len(titles)} matching elements\n")

    for i, title in enumerate(titles[:5]):
        print(f"--- Result {i+1} ---")
        print(title.inner_text())
        print()

    page.screenshot(path="search_results.png")
    browser.close()