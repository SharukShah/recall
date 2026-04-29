"""
Behavioral service — STAR story capture, practice, and evaluation.
"""
import logging
import random
from pathlib import Path

from openai import AsyncOpenAI
import asyncpg

from core.db_queries import (
    insert_capture,
    create_star_story,
    list_star_stories,
    get_star_story,
    update_star_story,
    delete_star_story,
    get_behavioral_coverage,
    increment_story_practice,
)
from models.behavioral_models import StarExtraction, BehavioralEvaluationLLM

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
MODEL_NANO = "gpt-4.1-nano"
MODEL_MINI = "gpt-4.1-mini"

ALLOWED_COMPETENCIES = {
    "leadership", "teamwork", "conflict_resolution", "problem_solving",
    "communication", "adaptability", "initiative", "failure_handling",
}

BEHAVIORAL_QUESTION_BANK = {
    "leadership": [
        "Tell me about a time you led a team through a challenging project.",
        "Describe a situation where you had to make a difficult decision as a leader.",
        "Give an example of how you motivated a team member who was underperforming.",
    ],
    "teamwork": [
        "Tell me about a time when you had to work with a difficult team member.",
        "Describe a project where cross-team collaboration was critical to success.",
        "Give an example of how you contributed to a team goal beyond your assigned role.",
    ],
    "conflict_resolution": [
        "Tell me about a time you resolved a disagreement between team members.",
        "Describe a situation where you had to handle a conflict with a stakeholder.",
        "Give an example of a technical disagreement you resolved constructively.",
    ],
    "problem_solving": [
        "Tell me about the most complex problem you've solved at work.",
        "Describe a situation where you had to find a creative solution with limited resources.",
        "Give an example of how you debugged a critical production issue.",
    ],
    "communication": [
        "Tell me about a time you had to explain a complex technical concept to a non-technical audience.",
        "Describe a situation where miscommunication led to a problem and how you fixed it.",
        "Give an example of how you delivered difficult feedback to a colleague.",
    ],
    "adaptability": [
        "Tell me about a time when project requirements changed significantly mid-way.",
        "Describe a situation where you had to quickly learn a new technology or tool.",
        "Give an example of how you adapted to a major change in your team or organization.",
    ],
    "initiative": [
        "Tell me about a time you identified and solved a problem before it became critical.",
        "Describe a project or improvement you initiated without being asked.",
        "Give an example of how you went above and beyond your job responsibilities.",
    ],
    "failure_handling": [
        "Tell me about a time you failed at something. What did you learn?",
        "Describe a project that didn't go as planned. How did you handle it?",
        "Give an example of a mistake you made and how you recovered from it.",
    ],
}


def _load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


class BehavioralService:
    def __init__(self, db_pool: asyncpg.Pool, openai_client: AsyncOpenAI):
        self.db_pool = db_pool
        self.openai = openai_client

    async def capture_story(self, narrative: str, competency: str) -> dict:
        if competency not in ALLOWED_COMPETENCIES:
            raise ValueError(f"Invalid competency: {competency}")

        # Store narrative as a capture
        capture_id = await insert_capture(
            self.db_pool, narrative, "behavioral", None
        )

        # Extract STAR via LLM
        extraction_prompt = _load_prompt("behavioral_extraction.txt")
        response = await self.openai.responses.parse(
            model=MODEL_NANO,
            instructions=extraction_prompt,
            input=f"<user_input>\n{narrative}\n</user_input>",
            text_format=StarExtraction,
            temperature=0.3,
            max_output_tokens=800,
        )
        star = response.output_parsed

        # Evaluate quality for strength_rating
        eval_prompt = _load_prompt("behavioral_evaluation.txt")
        eval_input = eval_prompt.format(
            question=f"Behavioral story about {competency}",
            competency=competency,
            user_answer=narrative,
        )
        eval_response = await self.openai.responses.parse(
            model=MODEL_MINI,
            instructions=eval_input,
            input="Rate this behavioral story.",
            text_format=BehavioralEvaluationLLM,
            temperature=0.2,
            max_output_tokens=500,
        )
        strength_rating = eval_response.output_parsed.overall_score

        # Insert story
        story_id = await create_star_story(
            self.db_pool,
            capture_id=capture_id,
            title=star.title,
            situation=star.situation,
            task=star.task,
            action=star.action,
            result=star.result,
            competency=competency,
            strength_rating=strength_rating,
        )

        return {
            "story_id": story_id,
            "capture_id": capture_id,
            "title": star.title,
            "situation": star.situation,
            "task": star.task,
            "action": star.action,
            "result": star.result,
            "competency": competency,
            "strength_rating": strength_rating,
        }

    async def list_stories(
        self, competency: str | None, limit: int, offset: int
    ) -> dict:
        return await list_star_stories(self.db_pool, competency, limit, offset)

    async def get_story(self, story_id: str) -> dict | None:
        return await get_star_story(self.db_pool, story_id)

    async def update_story(self, story_id: str, updates: dict) -> dict | None:
        return await update_star_story(self.db_pool, story_id, updates)

    async def delete_story(self, story_id: str) -> bool:
        return await delete_star_story(self.db_pool, story_id)

    async def get_practice_question(self, competency: str | None) -> dict:
        if competency and competency not in ALLOWED_COMPETENCIES:
            raise ValueError(f"Invalid competency: {competency}")

        # Pick competency — prefer under-covered ones
        if not competency:
            coverage = await get_behavioral_coverage(self.db_pool)
            # Sort by story_count ascending, pick from least covered
            sorted_coverage = sorted(coverage, key=lambda c: c["story_count"])
            competency = sorted_coverage[0]["competency"]

        # Pick a random question from the bank
        questions = BEHAVIORAL_QUESTION_BANK.get(competency, [])
        question = random.choice(questions) if questions else (
            f"Tell me about a time you demonstrated {competency.replace('_', ' ')}."
        )

        tips = (
            "Remember to use the STAR framework: specific Situation, clear Task, "
            "your individual Action (say 'I' not 'we'), and a measurable Result."
        )

        return {
            "question": question,
            "competency": competency,
            "tips": tips,
        }

    async def evaluate_practice_answer(
        self, competency: str, question: str, answer: str
    ) -> dict:
        if competency not in ALLOWED_COMPETENCIES:
            raise ValueError(f"Invalid competency: {competency}")

        eval_prompt = _load_prompt("behavioral_evaluation.txt")
        prompt = eval_prompt.format(
            question=question,
            competency=competency,
            user_answer=answer,
        )

        response = await self.openai.responses.parse(
            model=MODEL_MINI,
            instructions=prompt,
            input="Evaluate this behavioral answer.",
            text_format=BehavioralEvaluationLLM,
            temperature=0.2,
            max_output_tokens=500,
        )
        result = response.output_parsed

        return {
            "situation_score": result.situation_score,
            "task_score": result.task_score,
            "action_score": result.action_score,
            "result_score": result.result_score,
            "overall_score": result.overall_score,
            "feedback": result.feedback,
            "suggestions": result.suggestions,
        }

    async def get_coverage(self) -> dict:
        coverage = await get_behavioral_coverage(self.db_pool)
        covered = sum(1 for c in coverage if c["story_count"] > 0)
        return {
            "competencies": coverage,
            "total_competencies": len(ALLOWED_COMPETENCIES),
            "covered_competencies": covered,
        }
