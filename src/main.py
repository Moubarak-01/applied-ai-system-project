from __future__ import annotations

import sys

from src.core.models import UserProfile
from src.core.recommender import MusicRecommender


def run_basic() -> None:
    """Run the basic content-based recommender with a static profile."""
    recommender = MusicRecommender()

    profile = UserProfile(
        preferred_genres=["electronic", "hip-hop"],
        mood="energetic",
        energy_level=0.8,
        context="working out",
    )

    print(f"Profile: {profile}\n")
    results = recommender.recommend(profile)

    print(f"Top {len(results)} recommendations:\n")
    for i, rec in enumerate(results, 1):
        print(f"  {i}. {rec.song.title} by {rec.song.artist} "
              f"(score: {rec.score})")
        print(f"     {rec.reasoning}")
        if rec.fun_fact:
            print(f"     Fun Fact: {rec.fun_fact}")
        print()


def run_agent() -> None:
    """Run the agentic Mood-Seeker interview loop."""
    from src.agent.mood_seeker import MoodSeekerAgent

    agent = MoodSeekerAgent()
    agent.run()


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "basic"

    if mode == "agent":
        run_agent()
    else:
        run_basic()


if __name__ == "__main__":
    main()
