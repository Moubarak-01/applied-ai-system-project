from __future__ import annotations

import csv
import re
from pathlib import Path

from src.core.models import Recommendation, Song, UserProfile


def _normalize_genre(genre: str) -> str:
    """Normalize a genre string for fuzzy comparison.

    Lowercases, strips whitespace, and removes hyphens/spaces so that
    'Hip-Hop', 'hip hop', 'hiphop', and 'Hip Hop' all become 'hiphop'.
    """
    return re.sub(r"[\s\-]+", "", genre.strip().lower())

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# Mini knowledge base for RAG-style fun facts, keyed by artist or genre.
FUN_FACTS: dict[str, str] = {
    # Artists
    "the weeknd": "The Weeknd's 'Blinding Lights' spent 90 weeks on the Billboard Hot 100, the longest-charting song at the time.",
    "queen": "Freddie Mercury reportedly recorded vocal tracks for 'Bohemian Rhapsody' so many times the tape nearly wore through.",
    "debussy": "Debussy composed 'Clair de Lune' in 1890 but didn't publish it until 1905 — 15 years later.",
    "eminem": "Eminem wrote 'Lose Yourself' on set during breaks from filming 8 Mile.",
    "childish gambino": "Donald Glover chose the name 'Childish Gambino' from a Wu-Tang Clan name generator.",
    "deadmau5": "Deadmau5's 'Strobe' is widely considered one of the greatest electronic tracks ever made by fan polls.",
    "ludovico einaudi": "Einaudi once performed on a floating platform in the Arctic Ocean to raise awareness about climate change.",
    "travis scott": "'Sicko Mode' seamlessly blends three different beats in a single track — unusual for a hit single.",
    "adele": "Adele's '21' is one of the best-selling albums of all time, with over 31 million copies sold worldwide.",
    "daft punk": "Daft Punk recorded 'Get Lucky' with Nile Rodgers, who played the guitar riff in a single take.",
    "marconi union": "'Weightless' was scientifically engineered with sound therapists to reduce anxiety by up to 65%.",
    "kendrick lamar": "Kendrick Lamar was the first rapper to win a Pulitzer Prize for Music.",
    "m83": "M83 is named after the galaxy Messier 83, reflecting the band's 'cosmic' sound ambitions.",
    "lord huron": "Lord Huron builds fictional worlds for each album — 'Strange Trails' has its own mythology and characters.",
    "mgmt": "MGMT wrote 'Electric Feel' after experimenting with African-influenced rhythms in their dorm room.",
    "sia": "Sia started wearing her iconic wig to preserve her anonymity after years of struggling with fame.",
    "skrillex": "Skrillex was the lead singer of a post-hardcore band called From First to Last before going electronic.",
    "billy joel": "Billy Joel has never sold the publishing rights to his songs despite reportedly being offered over $100 million.",
    # Genres
    "pop": "Pop music gets its name from 'popular' — the genre has dominated global charts since the 1950s.",
    "rock": "The term 'rock and roll' was originally 1950s slang before it became a genre name.",
    "hip-hop": "Hip-hop originated in the Bronx in 1973, when DJ Kool Herc began isolating percussion breaks.",
    "electronic": "The first fully electronic instrument, the Theremin, was invented in 1920 — over a century ago.",
    "classical": "Classical music can lower blood pressure — hospitals sometimes play it during surgery.",
    "r&b": "R&B stands for 'Rhythm and Blues', coined by Billboard journalist Jerry Wexler in 1948.",
    "indie": "'Indie' originally meant independently released music, but it evolved into its own sound and aesthetic.",
    "ambient": "Brian Eno coined the term 'ambient music' in 1978 with his album 'Music for Airports'.",
}


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
                        fun_fact=self._fun_fact(song),
                    )
                )

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    def _score(self, song: Song, profile: UserProfile) -> float:
        score = 0.0

        # Genre match (fuzzy: ignores case, hyphens, spaces)
        song_genre = _normalize_genre(song.genre)
        if song_genre in [_normalize_genre(g) for g in profile.preferred_genres]:
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
        song_genre = _normalize_genre(song.genre)
        if song_genre in [_normalize_genre(g) for g in profile.preferred_genres]:
            reasons.append(f"genre match ({song.genre})")
        if song.mood.lower() == profile.mood.lower():
            reasons.append(f"mood match ({song.mood})")
        energy_diff = abs(song.energy - profile.energy_level)
        if energy_diff < 0.3:
            reasons.append("similar energy level")
        return ", ".join(reasons) if reasons else "partial match"

    @staticmethod
    def _fun_fact(song: Song) -> str:
        """Look up a fun fact by artist first, then fall back to genre."""
        return (
            FUN_FACTS.get(song.artist.lower())
            or FUN_FACTS.get(song.genre.lower(), "")
        )
