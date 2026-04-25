"""Pydantic models for mnemonic generation LLM structured output."""
from pydantic import BaseModel
from typing import Literal


class FactMnemonic(BaseModel):
    fact_index: int
    mnemonic_type: Literal["acronym", "analogy", "visual_hook", "rhyme", "none"]
    mnemonic_text: str | None = None


class MnemonicSet(BaseModel):
    mnemonics: list[FactMnemonic]
