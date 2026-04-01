from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Song:
    title: str
    artist: str
    genre: str
    mood: str
    energy: float  # 0.0 (calm) to 1.0 (intense)
    tempo: int  # BPM


@dataclass
class UserProfile:
    preferred_genres: list[str] = field(default_factory=list)
    mood: str = ""
    energy_level: float = 0.5
    context: str = ""  # e.g. "working out", "studying", "relaxing"


@dataclass
class Recommendation:
    song: Song
    score: float  # 0.0 to 1.0 relevance score
    reasoning: str = ""
