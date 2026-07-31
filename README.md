# Browser AI Agent Platform

An AI agent that completes browser-based tasks (search, price comparison, summarization)
described in plain English, using an LLM for decision-making and Playwright for browser control.

## Stack
- Backend: FastAPI + Playwright + Groq (Llama 3.3 70B)
- Frontend: React (Vite)

## Running locally
1. Backend: `uvicorn main:app --reload`
2. Frontend: `cd frontend && npm run dev`