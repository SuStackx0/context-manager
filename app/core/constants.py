"""Shared constants and enums."""
from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class MemoryCategory(str, Enum):
    profession = "profession"
    technology = "technology"
    preference = "preference"
    goal = "goal"
    topic = "topic"


# Context section priorities (lower number = filled first / dropped last).
class SectionPriority(int, Enum):
    memories = 1
    summaries = 2
    recent = 3
    retrieved = 4
