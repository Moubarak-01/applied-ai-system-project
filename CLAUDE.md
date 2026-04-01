# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands

```bash
pip install -r requirements.txt       # install dependencies
python -m src.main                     # run basic recommender (no API key needed)
python -m src.main agent               # run agentic Mood-Seeker (requires GEMINI_API_KEY)
```

Copy `.env.example` to `.env` and fill in your API key before using the agent mode.

## Architecture

This is a modular Applied AI music recommendation system with three layers:

- **src/core/** — Pure recommendation logic. `models.py` defines dataclasses (`Song`, `UserProfile`, `Recommendation`). `recommender.py` is a content-based engine that scores songs by genre, mood, and energy match against a `UserProfile`. No LLM dependency.
- **src/agent/** — Agentic workflow. `mood_seeker.py` implements a 3-step loop: (1) interview the user about their vibe, (2) use an LLM to parse answers into a `UserProfile`, (3) run the recommender then have the LLM critique/filter results for mood fit. Uses Google Gemini API.
- **src/rag/** — Placeholder for RAG pipeline. `retriever.py` stubs out vector-based song retrieval to augment the content-based engine.

Data lives in `data/raw/` (source CSVs) and `data/processed/` (transformed artifacts). Architecture diagrams go in `assets/`.

## Code Style

- Python 3.10+, type hints throughout, `from __future__ import annotations`
- Dataclasses for data models, no ORMs
- Imports use package-relative paths (`from src.core.models import ...`)
- Run from project root as a module (`python -m src.main`)
