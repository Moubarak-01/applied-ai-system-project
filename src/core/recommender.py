from __future__ import annotations

import csv
from pathlib import Path

from src.core.models import Recommendation, Song, UserProfile

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


class MusicRecommender:
    """Content-based music recommender. No LLM dependency."""

    def __init__(self, catalog_path: Path | None = None) -> None:
        self.catalog_path = catalog_path or DATA_DIR / "songs.csv"
        self.songs: list[Song] = []
        self._load_catalog()

    def _load_catalog(self) -> None:
        with open(self.catalog_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.songs.append(
                    Song(
                        title=row["title"],
                        artist=row["artist"],
                        genre=row["genre"],
                        mood=row["mood"],
                        energy=float(row["energy"]),
                        tempo=int(row["tempo"]),
                    )
                )

    def recommend(
        self, profile: UserProfile, top_k: int = 5
    ) -> list[Recommendation]:
        scored: list[Recommendation] = []

        for song in self.songs:
            score = self._score(song, profile)
            if score > 0:
                scored.append(
                    Recommendation(
                        song=song,
                        score=round(score, 3),
                        reasoning=self._explain(song, profile),
                    )
                )

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    def _score(self, song: Song, profile: UserProfile) -> float:
        score = 0.0

        # Genre match
        if song.genre.lower() in [g.lower() for g in profile.preferred_genres]:
            score += 0.4

        # Mood match
        if song.mood.lower() == profile.mood.lower():
            score += 0.35

        # Energy proximity (closer = better)
        energy_diff = abs(song.energy - profile.energy_level)
        score += 0.25 * (1 - energy_diff)

        return score

    def _explain(self, song: Song, profile: UserProfile) -> str:
        reasons: list[str] = []
        if song.genre.lower() in [g.lower() for g in profile.preferred_genres]:
            reasons.append(f"genre match ({song.genre})")
        if song.mood.lower() == profile.mood.lower():
            reasons.append(f"mood match ({song.mood})")
        energy_diff = abs(song.energy - profile.energy_level)
        if energy_diff < 0.3:
            reasons.append("similar energy level")
        return ", ".join(reasons) if reasons else "partial match"
