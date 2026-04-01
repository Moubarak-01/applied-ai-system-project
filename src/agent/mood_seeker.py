from __future__ import annotations

import json
import os
import re

from dotenv import load_dotenv
import google.generativeai as genai

from src.core.models import Recommendation, UserProfile
from src.core.recommender import MusicRecommender

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

VIBE_QUESTIONS = [
    "How was your day?",
    "What is your current energy level (1-10)?",
    "What genre are you craving?",
]


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers that Gemini sometimes adds."""
    return re.sub(r"^```(?:json)?\s*\n?|```\s*$", "", text.strip(), flags=re.MULTILINE).strip()


class MoodSeekerAgent:
    """Agentic loop: interview -> build profile -> recommend -> critique."""

    def __init__(self) -> None:
        self.model = genai.GenerativeModel("gemini-2.0-flash")
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
            "You are a music taste analyst. Based on the user's interview answers, "
            "return a JSON object with these keys:\n"
            "- preferred_genres: list of strings from [pop, rock, hip-hop, electronic, "
            "classical, r&b, indie, ambient]. Use the genre they mentioned plus any "
            "closely related genres.\n"
            "- mood: one of [happy, melancholy, calm, energetic, motivated, chill]. "
            "Infer from how their day went.\n"
            "- energy_level: float 0.0-1.0. Convert their 1-10 rating by dividing "
            "by 10.\n"
            "- context: a short string summarising their current situation based on "
            "their answers.\n\n"
            f"Q1: {VIBE_QUESTIONS[0]}\nA1: {answers[0]}\n"
            f"Q2: {VIBE_QUESTIONS[1]}\nA2: {answers[1]}\n"
            f"Q3: {VIBE_QUESTIONS[2]}\nA3: {answers[2]}\n\n"
            "Return ONLY valid JSON, no markdown."
        )

        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.3),
        )

        data = json.loads(_strip_markdown_fences(response.text))
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
            "Return a JSON array of objects with keys: title (must match exactly "
            "as shown above), keep (bool), reasoning (string). Only set "
            "keep=false for songs that are a genuinely bad fit. When in doubt, "
            "keep the song. Return ONLY valid JSON, no markdown."
        )

        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.3),
        )

        verdicts = json.loads(_strip_markdown_fences(response.text))
        # Normalize titles for lookup (handles curly quotes, extra spaces, etc.)
        verdict_map = {v["title"].strip().lower(): v for v in verdicts}

        filtered: list[Recommendation] = []
        for rec in recommendations:
            verdict = verdict_map.get(rec.song.title.strip().lower())
            # Default to keeping the song if the LLM didn't mention it
            if verdict is None or verdict.get("keep", True):
                if verdict:
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
            print(f"     {rec.reasoning}")
            if rec.fun_fact:
                print(f"     Fun Fact: {rec.fun_fact}")
            print()

        return final
