# Model Card: Applied AI Music Recommender

## Intended Use

A music recommendation system that uses an agentic workflow to interview users about their current mood, parse their natural language responses into structured profiles via the Gemini API, and return personalized song recommendations with a self-critique quality check.

## Data Description

The system uses a curated catalog of 20 songs (`data/raw/songs.csv`) with attributes: title, artist, genre, mood, energy (0.0-1.0), and tempo (BPM). Genres covered: pop, rock, classical, hip-hop, r&b, electronic, ambient, indie.

## System Reflection

Using an LLM as a "normalizer" between the user and the recommendation engine is what makes this system robust. A traditional keyword-matching approach would struggle with input like "Amazing! Just crushed a personal record at the gym" because there is no explicit mention of energy or mood. But the LLM understands the intent behind the words, correctly mapping that statement to `mood=happy` and `energy=0.9`. This translation layer means users can speak naturally without worrying about matching the system's internal schema, and the core engine still receives clean, structured data to score against. It turns a rigid filtering problem into a conversational experience.

The 4/5 confidence scores reveal an interesting trade-off between vibe accuracy and genre strictness. For example, the Gym-goer persona asked specifically for hip-hop, but the system also recommended "Blinding Lights" (pop) and "Don't Stop Me Now" (rock) because they matched the user's high energy and happy mood almost perfectly. The self-critique acknowledged these as strong fits despite the genre mismatch. Arguably, a user who just crushed a PR would enjoy those tracks regardless. This shows that the system prioritizes overall vibe over rigid genre filtering, which is a deliberate design choice: mood and energy matter more than labels. A future improvement could let users specify how strictly they want genre enforced, giving them control over this balance.

## Solved Engineering Challenges

1. **Gemini Markdown Fence Wrapping.** Gemini returns JSON wrapped in ` ```json ``` ` fences despite being told not to. Solved with a `_strip_markdown_fences()` regex sanitizer applied before every `json.loads()` call.
2. **LLM Mood Ambiguity.** The same input ("terrible day") can reasonably map to "calm", "melancholy", or "chill". Solved by accepting multiple valid moods per test persona instead of a single expected value.
3. **Energy Scale Normalization.** Users give energy as 1-10 but the recommender expects 0.0-1.0. Solved by instructing the LLM to divide by 10 in the profile extraction prompt.
4. **Vibe vs. Genre Strictness Trade-off.** The scoring algorithm sometimes ranks a perfect mood/energy match above a genre match. This is by design (mood and energy carry 60% of the score weight), but surfaced as 4/5 confidence in self-critique.
5. **Deprecated SDK Warning.** The `google.generativeai` package is deprecated in favor of `google-genai`. Currently pinned to the older package; migration is planned.
6. **OpenAI to Gemini Migration.** Originally built on OpenAI, but quota limits required a full migration to Gemini. Refactored all LLM calls, prompt formatting, and response parsing across agent and test modules.
7. **RAG-Style Fun Facts Without a Vector DB.** Instead of a full RAG pipeline, implemented a lightweight dictionary-based knowledge base keyed by artist and genre, giving each recommendation a personalized fun fact with zero latency overhead.

## Limitations

- **Small song database.** The catalog contains only 20 songs across 8 genres. A user requesting niche genres (e.g. jazz, metal, country) will get zero genre matches, falling back to mood/energy scoring only.
- **No persistent user history.** The system does not remember past sessions or learn from repeated interactions. Every run starts from scratch.
- **Single-language support.** The interview and LLM prompts are English-only. Non-English input may produce unpredictable profile extractions.
- **LLM non-determinism.** The same user input can produce slightly different profiles across runs because LLM outputs are inherently variable, even at low temperature settings.
- **No audio analysis.** Recommendations are based on metadata (genre, mood, energy labels) rather than actual audio features. A song labeled "calm" might not feel calm to every listener.
- **API dependency.** The agentic workflow requires a live Gemini API connection and a valid key. The basic recommender works offline, but the full experience does not.

## How AI Helped Me Build This

- **Regex for JSON cleaning.** AI helped write the `_strip_markdown_fences()` regex pattern that strips ` ```json ``` ` wrappers from Gemini responses, which was the root cause of repeated `JSONDecodeError` crashes during development.
- **Prompt engineering.** AI assisted in designing the profile extraction prompt so that the LLM reliably outputs valid JSON with the correct keys and value types, including the energy scale conversion from 1-10 to 0.0-1.0.
- **Test persona design.** AI helped design the three reliability test personas with appropriate expected mood ranges and energy bounds, making the test suite resilient to valid LLM interpretation differences.
- **Fuzzy genre matching.** AI helped implement the `_normalize_genre()` function to handle inconsistencies between how users type genres and how they appear in the CSV.
- **Project scaffolding.** AI assisted in structuring the modular directory layout (core/agent/rag) and writing the initial boilerplate code, letting me focus on the AI integration and evaluation logic.

## Evaluation

Tested with 3 simulated personas. Results:

| Persona | Mood | Energy | Self-Critique |
| --- | --- | --- | --- |
| Exhausted Office Worker | PASS | PASS | 5/5 |
| Hyped Gym-goer | PASS | PASS | 4/5 |
| Melancholic Student | PASS | PASS | 4/5 |

100% pass rate on mood and energy extraction. Average self-critique confidence: 4.3/5.

## Personal Reflection

This project demonstrates my ability to build agentic AI systems that bridge the gap between natural language and structured data. By implementing a self-critique loop and a rigorous test harness, I've created a recommender that is not only functional but measurably reliable.
