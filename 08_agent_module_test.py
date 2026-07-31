from agent.core import run_agent

if __name__ == "__main__":
    # Task 3: a genuinely different task type — page summarization, not search/shopping
    run_agent(
        task="Summarize what this website is about in 2-3 sentences",
        start_url="https://en.wikipedia.org/wiki/Web_scraping"
    )