from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from src.core.models import Recommendation, UserProfile
from src.core.recommender import MusicRecommender

load_dotenv()

VIBE_QUESTIONS = [
    "How are you feeling right now in one or two words?",
    "What are you about to do? (e.g. studying, working out, driving, chilling)",
    "Pick a vibe: upbeat & energetic, mellow & reflective, or somewhere in between?",
]


class MoodSeekerAgent:
    """Agentic loop: interview -> build profile -> recommend -> critique."""

    def __init__(self) -> None:
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.recommender = MusicRecommender()

    # -- Step 1: Interview --------------------------------------------------

    def interview(self) -> list[str]:
        answers: list[str] = []
        print("\n--- Mood-Seeker Interview ---\n")
        for q in VIBE_QUESTIONS:
            answer = input(f"  {q}\n  > ")
            answers.append(answer.strip())
        return answers

    # -- Step 2: Build profile via LLM -------------------------------------

    def build_profile(self, answers: list[str]) -> UserProfile:
        prompt = (
            "You are a music taste analyst. Based on these answers, return a JSON "
            "object with keys: preferred_genres (list of strings from: pop, rock, "
            "hip-hop, electronic, classical, r&b, indie, ambient), mood (one of: "
            "happy, melancholy, calm, energetic, motivated, chill), energy_level "
            "(float 0-1), and context (short string).\n\n"
            f"Q1: {VIBE_QUESTIONS[0]}\nA1: {answers[0]}\n"
            f"Q2: {VIBE_QUESTIONS[1]}\nA2: {answers[1]}\n"
            f"Q3: {VIBE_QUESTIONS[2]}\nA3: {answers[2]}\n\n"
            "Return ONLY valid JSON, no markdown."
        )

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        data = json.loads(response.choices[0].message.content)
        return UserProfile(
            preferred_genres=data.get("preferred_genres", []),
            mood=data.get("mood", ""),
            energy_level=float(data.get("energy_level", 0.5)),
            context=data.get("context", ""),
        )

    # -- Step 3: Critique & re-rank ----------------------------------------

    def critique(
        self, recommendations: list[Recommendation], profile: UserProfile
    ) -> list[Recommendation]:
        if not recommendations:
            return recommendations

        songs_text = "\n".join(
            f"- {r.song.title} by {r.song.artist} "
            f"(genre={r.song.genre}, mood={r.song.mood}, energy={r.song.energy})"
            for r in recommendations
        )

        prompt = (
            "You are a music critic. The user's vibe: "
            f"mood={profile.mood}, energy={profile.energy_level}, "
            f"context={profile.context}, genres={profile.preferred_genres}.\n\n"
            f"Recommended songs:\n{songs_text}\n\n"
            "Return a JSON array of objects with keys: title, keep (bool), "
            "reasoning (string). Set keep=false for songs that don't match "
            "the user's actual vibe. Return ONLY valid JSON, no markdown."
        )

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        verdicts = json.loads(response.choices[0].message.content)
        verdict_map = {v["title"]: v for v in verdicts}

        filtered: list[Recommendation] = []
        for rec in recommendations:
            verdict = verdict_map.get(rec.song.title)
            if verdict and verdict.get("keep", True):
                rec.reasoning = verdict.get("reasoning", rec.reasoning)
                filtered.append(rec)

        return filtered

    # -- Orchestrator -------------------------------------------------------

    def run(self) -> list[Recommendation]:
        answers = self.interview()

        print("\nAnalyzing your vibe...")
        profile = self.build_profile(answers)
        print(f"  Profile: mood={profile.mood}, energy={profile.energy_level}, "
              f"context={profile.context}")

        print("\nFinding songs...")
        recommendations = self.recommender.recommend(profile, top_k=8)

        print("Critiquing recommendations...")
        final = self.critique(recommendations, profile)

        print(f"\n--- Your {len(final)} Mood-Matched Songs ---\n")
        for i, rec in enumerate(final, 1):
            print(f"  {i}. {rec.song.title} by {rec.song.artist}")
            print(f"     {rec.reasoning}\n")

        return final
