"""Shared types and enums used across models."""
from typing import Literal

ContentType = Literal["fact", "concept", "list", "comparison", "procedure"]
QuestionType = Literal["recall", "cloze", "explain", "connect", "apply"]
TechniqueType = Literal["chunking", "mnemonic", "elaboration", "visualization", "analogy", "none"]
ScoreType = Literal["correct", "partial", "wrong"]
