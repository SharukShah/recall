"""
OpenAI LLM client wrapper.
Handles all LLM calls with structured outputs using Pydantic models.
Model tiering: GPT-4.1-nano for extraction/questions/technique, GPT-4.1-mini for evaluation/synthesis.
"""
import json
import logging
from pathlib import Path
from openai import AsyncOpenAI

from models.capture_models import ExtractedFacts, GeneratedQuestions, TechniqueSelection
from models.review_models import AnswerEvaluation

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

MODEL_NANO = "gpt-4.1-nano"
MODEL_MINI = "gpt-4.1-mini"


def _load_prompt(filename: str) -> str:
    """Load a system prompt from the prompts directory."""
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


async def extract_facts(client: AsyncOpenAI, raw_text: str, why_it_matters: str | None = None) -> ExtractedFacts:
    """
    Extract structured facts from raw text using LLM.
    Returns ExtractedFacts with topic and list of Fact objects.
    """
    system_prompt = _load_prompt("extraction.txt")
    user_message = f"<user_input>\n{raw_text}\n</user_input>"
    if why_it_matters:
        user_message += f"\n\nContext (why this matters to me): <user_input>{why_it_matters}</user_input>"

    response = await client.responses.parse(
        model=MODEL_NANO,
        instructions=system_prompt,
        input=user_message,
        text_format=ExtractedFacts,
        temperature=0.3,
        max_output_tokens=2000,
    )
    return response.output_parsed


async def generate_questions(client: AsyncOpenAI, facts: list[dict]) -> GeneratedQuestions:
    """
    Generate review questions from extracted facts.
    Returns GeneratedQuestions with list of question objects.
    """
    system_prompt = _load_prompt("question_generation.txt")
    user_message = json.dumps(facts, indent=2)

    response = await client.responses.parse(
        model=MODEL_NANO,
        instructions=system_prompt,
        input=user_message,
        text_format=GeneratedQuestions,
        temperature=0.5,
        max_output_tokens=2000,
    )
    return response.output_parsed


async def select_technique(client: AsyncOpenAI, facts: list[dict]) -> TechniqueSelection:
    """
    Select optimal memory technique for the given facts.
    Returns TechniqueSelection with technique name and instructions.
    """
    system_prompt = _load_prompt("technique_selection.txt")
    user_message = json.dumps(facts, indent=2)

    response = await client.responses.parse(
        model=MODEL_NANO,
        instructions=system_prompt,
        input=user_message,
        text_format=TechniqueSelection,
        temperature=0.2,
        max_output_tokens=500,
    )
    return response.output_parsed


async def evaluate_answer(
    client: AsyncOpenAI,
    question_text: str,
    expected_answer: str,
    user_answer: str,
) -> AnswerEvaluation:
    """
    Evaluate user's answer against expected answer.
    Returns AnswerEvaluation with score, feedback, and suggested rating.
    """
    system_prompt = _load_prompt("answer_evaluation.txt")
    user_message = (
        f"Question: {question_text}\n"
        f"Expected answer: {expected_answer}\n"
        f"User's answer: <user_input>{user_answer}</user_input>"
    )

    response = await client.responses.parse(
        model=MODEL_MINI,
        instructions=system_prompt,
        input=user_message,
        text_format=AnswerEvaluation,
        temperature=0.2,
        max_output_tokens=500,
    )
    return response.output_parsed
