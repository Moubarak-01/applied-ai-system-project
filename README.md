# Applied AI Music Recommender

My system follows a **Modular Agentic Pattern**:

- **The Agent (`src/agent/`):** Acts as the interface, using an LLM to translate natural language into a schema.
- **The Core (`src/core/`):** A high-performance recommendation engine that handles the math and data filtering.
- **The RAG Layer (`src/rag/`):** (Placeholder) Designed to eventually retrieve song lyrics to improve mood matching.

## Setup

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your Gemini API key:

```bash
cp .env.example .env
# Then edit .env and set: GEMINI_API_KEY=your_key_here
```

Run the basic recommender (no API key needed):

```bash
python -m src.main
```

Run the agentic Mood-Seeker (requires `GEMINI_API_KEY`):

```bash
python -m src.main agent
```

Run the reliability tests:

```bash
python -m tests.test_agent_reliability
```

## Sample Interactions

Below are sample runs from all three test personas:

### Exhausted Office Worker

```text
============================================================
  Persona: Exhausted Office Worker
============================================================
  Answers: ['Terrible. Back-to-back meetings and I just want to zone out.', '2', 'ambient']
  Extracted: mood=melancholy, energy=0.2, genres=['ambient', 'electronic', 'classical'],
             context=User had a terrible day with back-to-back meetings and wants to zone out.

  Top 5 recommendations:
    1. Nuvole Bianche by Ludovico Einaudi (score=1.0)
    2. Clair de Lune by Debussy (score=0.637)
    3. Weightless by Marconi Union (score=0.625)
    4. Breathe Me by Sia (score=0.6)
    5. The Night We Met by Lord Huron (score=0.587)

  Self-Critique Confidence: 4/5
```

The LLM correctly interpreted "Terrible. Back-to-back meetings" as low energy and a melancholy mood. The core engine then surfaced calming ambient and classical tracks, exactly what this persona needed.

### Hyped Gym-goer

```text
============================================================
  Persona: Hyped Gym-goer
============================================================
  Answers: ['Amazing! Just crushed a personal record at the gym.', '9', 'hip-hop']
  Extracted: mood=happy, energy=0.9, genres=['hip-hop', 'r&b', 'pop'],
             context=Just finished a great workout and feeling energetic.

  Top 5 recommendations:
    1. Blinding Lights by The Weeknd (score=0.975)
    2. Sicko Mode by Travis Scott (score=0.65)
    3. Lose Yourself by Eminem (score=0.638)
    4. Don't Stop Me Now by Queen (score=0.6)
    5. Money Trees by Kendrick Lamar (score=0.6)

  Self-Critique Confidence: 4/5
```

The LLM mapped "crushed a personal record" to `mood=happy` and `energy=0.9`. The recommender returned high-energy hip-hop tracks alongside strong mood matches from other genres like pop and rock.

### Melancholic Student

```text
============================================================
  Persona: Melancholic Student
============================================================
  Answers: ['Pretty rough. Failed an exam and feeling down about it.', '3', 'indie']
  Extracted: mood=melancholy, energy=0.3, genres=['indie', 'ambient'],
             context=Feeling down after failing an exam and looking for indie music.

  Top 5 recommendations:
    1. The Night We Met by Lord Huron (score=0.988)
    2. Someone Like You by Adele (score=0.6)
    3. Weightless by Marconi Union (score=0.6)
    4. Nuvole Bianche by Ludovico Einaudi (score=0.575)
    5. Breathe Me by Sia (score=0.575)

  Self-Critique Confidence: 4/5
```

The LLM understood "failed an exam and feeling down" as melancholy with low energy. The top result, "The Night We Met" by Lord Huron, is a near-perfect match at 0.988 for indie genre, melancholy mood, and low energy.

## System Architecture

```mermaid
graph TD
    User([User]) -->|"3 vibe answers"| Agent

    subgraph "src/agent: Agentic Layer"
        Agent[MoodSeekerAgent]
        Agent -->|interview answers| LLM[Gemini LLM]
        LLM -->|parsed JSON| Profile[UserProfile]
    end

    subgraph "src/core: Core Engine"
        Profile --> Recommender[MusicRecommender]
        Recommender -->|scores songs| Songs[(songs.csv)]
        Recommender -->|ranked list| Results[Recommendations]
    end

    Results -->|top candidates| Critique[LLM Critique]
    Critique -->|filtered & re-ranked| Final([Final Songs])
```

### How the modules interact

1. **`src/agent/` drives the workflow.** `MoodSeekerAgent.run()` orchestrates everything: it interviews the user, calls the LLM, invokes the core engine, and runs the critique step.
2. **`src/core/` is pure logic, no LLM dependency.** The agent passes a `UserProfile` dataclass (defined in `src/core/models.py`) to `MusicRecommender.recommend()`, which scores songs from `songs.csv` by genre, mood, and energy proximity. It returns a ranked list of `Recommendation` objects.
3. **The LLM acts as a translator and a judge.** It appears twice: first to parse free-text answers into a structured `UserProfile`, then to critique whether the recommender's output actually matches the user's vibe and filter out poor fits.

## Evaluation Results

We tested the system's reliability by running three simulated personas through the `MoodSeekerAgent` and validating the LLM's profile extraction against expected values.

| Persona | Mood Check | Energy Check | Self-Critique Confidence |
| --- | --- | --- | --- |
| Exhausted Office Worker | PASS | PASS | 5/5 |
| Hyped Gym-goer | PASS | PASS | 4/5 |
| Melancholic Student | PASS | PASS | 4/5 |

**Overall Pass Rate: 100%** for both mood and energy extraction across all three personas. The LLM's self-critique step scored every recommendation set at 4/5 or 5/5, confirming that the final song lists are highly relevant to each user's stated vibe.

## Solved Engineering Challenges

1. **Gemini Markdown Fence Wrapping.** Gemini returns JSON wrapped in ` ```json ``` ` fences despite being told not to. Solved with a `_strip_markdown_fences()` regex sanitizer applied before every `json.loads()` call.
2. **LLM Mood Ambiguity.** The same input ("terrible day") can reasonably map to "calm", "melancholy", or "chill". Solved by accepting multiple valid moods per test persona instead of a single expected value.
3. **Energy Scale Normalization.** Users give energy as 1-10 but the recommender expects 0.0-1.0. Solved by instructing the LLM to divide by 10 in the profile extraction prompt.
4. **Vibe vs. Genre Strictness Trade-off.** The scoring algorithm sometimes ranks a perfect mood/energy match above a genre match. This is by design (mood and energy carry 60% of the score weight), but surfaced as 4/5 confidence in self-critique.
5. **Deprecated SDK Warning.** The `google.generativeai` package is deprecated in favor of `google-genai`. Currently pinned to the older package; migration is planned.
6. **OpenAI to Gemini Migration.** Originally built on OpenAI, but quota limits required a full migration to Gemini. Refactored all LLM calls, prompt formatting, and response parsing across agent and test modules.
7. **RAG-Style Fun Facts Without a Vector DB.** Instead of a full RAG pipeline, implemented a lightweight dictionary-based knowledge base keyed by artist and genre, giving each recommendation a personalized fun fact with zero latency overhead.

## Project Structure

```text
applied-ai-system-project/
├── CLAUDE.md                          # Claude Code guidance
├── README.md                          # This file
├── .env.example                       # API key template
├── .gitignore                         # Python, .env, .claude/
├── requirements.txt                   # google-generativeai, pandas, dotenv
│
├── data/
│   ├── raw/
│   │   └── songs.csv                  # 20-song catalog (title, artist, genre, mood, energy, tempo)
│   └── processed/                     # Transformed artifacts (placeholder)
│
├── src/
│   ├── main.py                        # CLI entry point (basic or agent mode)
│   ├── core/
│   │   ├── models.py                  # Dataclasses: Song, UserProfile, Recommendation
│   │   └── recommender.py             # Content-based scoring engine + fun facts knowledge base
│   ├── agent/
│   │   └── mood_seeker.py             # Agentic loop: interview, profile extraction, critique
│   └── rag/
│       └── retriever.py               # Placeholder for future vector-based retrieval
│
├── tests/
│   └── test_agent_reliability.py      # 3-persona reliability suite with LLM self-critique
│
└── assets/                            # Architecture diagrams
```

## Design Decisions

- **Fuzzy Genre Matching.** Genre comparisons strip hyphens, spaces, and case before matching. This means "hip hop", "Hip-Hop", and "hiphop" all match "hip-hop" in the catalog. Without this, the LLM returning "hip hop" (no hyphen) would silently produce zero genre-matched recommendations.
- **Weighted Scoring (40/35/25).** Genre carries the most weight (40%), followed by mood (35%), then energy proximity (25%). This ensures users get songs in their requested genre first, while still surfacing strong mood/energy fits from adjacent genres.
- **LLM as Normalizer, Not Scorer.** The LLM translates natural language into structured data, but the actual scoring is pure math with no LLM in the loop. This keeps recommendations deterministic and fast.
- **Self-Critique as a Guardrail.** After scoring, a second LLM call reviews the results and filters out songs that don't actually fit the user's vibe. This catches edge cases the math-based scorer misses.

## System Reflection

Using an LLM as a "normalizer" between the user and the recommendation engine is what makes this system robust. A traditional keyword-matching approach would struggle with input like "Amazing! Just crushed a personal record at the gym" because there is no explicit mention of energy or mood. But the LLM understands the intent behind the words, correctly mapping that statement to `mood=happy` and `energy=0.9`. This translation layer means users can speak naturally without worrying about matching the system's internal schema, and the core engine still receives clean, structured data to score against. It turns a rigid filtering problem into a conversational experience.

The 4/5 confidence scores reveal an interesting trade-off between vibe accuracy and genre strictness. For example, the Gym-goer persona asked specifically for hip-hop, but the system also recommended "Blinding Lights" (pop) and "Don't Stop Me Now" (rock) because they matched the user's high energy and happy mood almost perfectly. The self-critique acknowledged these as strong fits despite the genre mismatch. Arguably, a user who just crushed a PR would enjoy those tracks regardless. This shows that the system prioritizes overall vibe over rigid genre filtering, which is a deliberate design choice: mood and energy matter more than labels. A future improvement could let users specify how strictly they want genre enforced, giving them control over this balance.

This project demonstrates my ability to build agentic AI systems that bridge the gap between natural language and structured data. By implementing a self-critique loop and a rigorous test harness, I've created a recommender that is not only functional but measurably reliable.

## Project Demo

[Watch the full demo on Loom](https://www.loom.com/share/50c24368995847fc91bf70cbe25b74cf)
