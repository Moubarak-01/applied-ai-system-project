"""Reliability & Evaluation tests for the Mood-Seeker Agent.

Simulates 3 user personas, validates LLM profile extraction, and runs a
self-critique confidence scoring step on the final recommendations.

Usage:
    python -m tests.test_agent_reliability
"""

from __future__ import annotations

import json
import os
import sys

from dotenv import load_dotenv
import google.generativeai as genai

from src.agent.mood_seeker import MoodSeekerAgent, VIBE_QUESTIONS, _strip_markdown_fences
from src.core.models import Recommendation, UserProfile

load_dotenv()

# ---------------------------------------------------------------------------
# Persona definitions: pre-set answers + expected LLM extraction
# ---------------------------------------------------------------------------

PERSONAS: list[dict] = [
    {
        "name": "Exhausted Office Worker",
        "answers": [
            "Terrible. Back-to-back meetings and I just want to zone out.",
            "2",
            "ambient",
        ],
        "expected_moods": ["calm", "melancholy", "chill"],
        "expected_energy_range": (0.1, 0.4),
    },
    {
        "name": "Hyped Gym-goer",
        "answers": [
            "Amazing! Just crushed a personal record at the gym.",
            "9",
            "hip-hop",
        ],
        "expected_moods": ["energetic", "happy", "motivated"],
        "expected_energy_range": (0.7, 1.0),
    },
    {
        "name": "Melancholic Student",
        "answers": [
            "Pretty rough. Failed an exam and feeling down about it.",
            "3",
            "indie",
        ],
        "expected_moods": ["melancholy", "calm"],
        "expected_energy_range": (0.1, 0.5),
    },
]


# ---------------------------------------------------------------------------
# Self-critique: LLM scores how well recommendations match the persona
# ---------------------------------------------------------------------------

def self_critique(
    model: genai.GenerativeModel,
    persona_name: str,
    answers: list[str],
    profile: UserProfile,
    recommendations: list[Recommendation],
) -> dict:
    """Ask the LLM to score recommendation quality on a 1-5 scale."""
    songs_text = "\n".join(
        f"  - {r.song.title} by {r.song.artist} "
        f"(genre={r.song.genre}, mood={r.song.mood}, energy={r.song.energy})"
        for r in recommendations
    )

    prompt = (
        f"You are evaluating a music recommendation system.\n\n"
        f"User persona: {persona_name}\n"
        f"Interview answers:\n"
        f"  Q: {VIBE_QUESTIONS[0]}  A: {answers[0]}\n"
        f"  Q: {VIBE_QUESTIONS[1]}  A: {answers[1]}\n"
        f"  Q: {VIBE_QUESTIONS[2]}  A: {answers[2]}\n\n"
        f"Extracted profile: mood={profile.mood}, energy={profile.energy_level}, "
        f"genres={profile.preferred_genres}, context={profile.context}\n\n"
        f"Top 5 recommended songs:\n{songs_text}\n\n"
        "Rate how well these songs match the user's input on a scale of 1-5:\n"
        "  1 = terrible mismatch\n"
        "  2 = mostly wrong\n"
        "  3 = acceptable\n"
        "  4 = good fit\n"
        "  5 = perfect match\n\n"
        "Return ONLY a JSON object with keys: confidence (int 1-5) and "
        "reasoning (string explaining your score). No markdown."
    )

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(temperature=0.3),
    )

    return json.loads(_strip_markdown_fences(response.text))


# ---------------------------------------------------------------------------
# Main test runner
# ---------------------------------------------------------------------------

def run_reliability_tests() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)

    agent = MoodSeekerAgent()
    model = agent.model

    all_passed = True
    results_summary: list[dict] = []

    for persona in PERSONAS:
        name = persona["name"]
        answers = persona["answers"]
        expected_moods = persona["expected_moods"]
        energy_lo, energy_hi = persona["expected_energy_range"]

        print(f"\n{'='*60}")
        print(f"  Persona: {name}")
        print(f"{'='*60}")
        print(f"  Answers: {answers}")

        # -- Step 1: Profile extraction ------------------------------------
        profile = agent.build_profile(answers)
        print(f"  Extracted: mood={profile.mood}, energy={profile.energy_level}, "
              f"genres={profile.preferred_genres}, context={profile.context}")

        mood_ok = profile.mood.lower() in expected_moods
        energy_ok = energy_lo <= profile.energy_level <= energy_hi

        print(f"  Mood check:   {'PASS' if mood_ok else 'FAIL'} "
              f"(got '{profile.mood}', expected one of {expected_moods})")
        print(f"  Energy check: {'PASS' if energy_ok else 'FAIL'} "
              f"(got {profile.energy_level}, expected {energy_lo}-{energy_hi})")

        if not (mood_ok and energy_ok):
            all_passed = False

        # -- Step 2: Recommendations ---------------------------------------
        recommendations = agent.recommender.recommend(profile, top_k=5)
        print(f"\n  Top {len(recommendations)} recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"    {i}. {rec.song.title} by {rec.song.artist} "
                  f"(score={rec.score})")

        # -- Step 3: Self-critique -----------------------------------------
        critique = self_critique(model, name, answers, profile, recommendations)
        confidence = critique.get("confidence", 0)
        reasoning = critique.get("reasoning", "")
        print(f"\n  Self-Critique Confidence: {confidence}/5")
        print(f"  Reasoning: {reasoning}")

        if confidence < 3:
            print(f"  WARNING: Low confidence for persona '{name}'")
            all_passed = False

        results_summary.append({
            "persona": name,
            "mood_pass": mood_ok,
            "energy_pass": energy_ok,
            "confidence": confidence,
        })

    # -- Summary ---------------------------------------------------------------
    print(f"\n{'='*60}")
    print("  RELIABILITY SUMMARY")
    print(f"{'='*60}")
    for r in results_summary:
        status = ("PASS" if r["mood_pass"] and r["energy_pass"]
                  and r["confidence"] >= 3 else "FAIL")
        print(f"  [{status}] {r['persona']}: "
              f"mood={'OK' if r['mood_pass'] else 'FAIL'}, "
              f"energy={'OK' if r['energy_pass'] else 'FAIL'}, "
              f"confidence={r['confidence']}/5")

    print()
    if all_passed:
        print("  All reliability checks PASSED.")
    else:
        print("  Some checks FAILED. Review output above.")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    run_reliability_tests()
