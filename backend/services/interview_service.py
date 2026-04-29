"""
Interview service — mock interview sessions with LLM-powered evaluation.
"""
import json
import logging
from pathlib import Path

from openai import AsyncOpenAI
from fsrs import Scheduler
import asyncpg

from core.db_queries import (
    create_mock_interview,
    insert_interview_answers,
    get_interview_answer,
    update_interview_answer,
    complete_mock_interview,
    list_mock_interviews,
    get_interview_detail,
    get_due_questions_by_category,
)
from models.interview_models import (
    InterviewAnswerEvaluation,
    GeneratedInterviewQuestions,
    InterviewSummaryLLM,
)

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
MODEL_NANO = "gpt-4.1-nano"
MODEL_MINI = "gpt-4.1-mini"

ALLOWED_TOPICS = {
    "python", "python_basics", "oop", "dsa", "system_design",
    "databases", "web_dev", "networking", "os_concepts", "testing",
    "devops", "behavioral", "general",
}
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}


def _load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


class InterviewService:
    def __init__(self, db_pool: asyncpg.Pool, openai_client: AsyncOpenAI, scheduler: Scheduler):
        self.db_pool = db_pool
        self.openai = openai_client
        self.scheduler = scheduler

    async def start_interview(
        self, topic: str, difficulty: str, duration_minutes: int
    ) -> dict:
        if topic not in ALLOWED_TOPICS:
            raise ValueError(f"Invalid topic: {topic}")
        if difficulty not in ALLOWED_DIFFICULTIES:
            raise ValueError(f"Invalid difficulty: {difficulty}")
        if duration_minutes not in (15, 30, 45):
            raise ValueError("Duration must be 15, 30, or 45 minutes")

        # Calculate question count: ~3-4 min per question
        question_count = max(3, duration_minutes // 4)

        # Try to load existing questions from DB
        category = topic
        existing = await get_due_questions_by_category(
            self.db_pool, [category], limit=question_count
        )

        questions_for_interview: list[dict] = []
        for q in existing:
            questions_for_interview.append({
                "question_id": str(q["id"]),
                "question_text": q["question_text"],
                "expected_answer": "",  # will be filled from DB
            })

        # If not enough, generate via LLM
        shortfall = question_count - len(questions_for_interview)
        if shortfall > 0:
            generated = await self._generate_questions(topic, difficulty, shortfall)
            for g in generated:
                questions_for_interview.append({
                    "question_id": None,
                    "question_text": g["question_text"],
                    "expected_answer": g["expected_answer"],
                })

        # Fill expected_answer for DB-sourced questions
        for q in questions_for_interview:
            if q["question_id"] and not q["expected_answer"]:
                async with self.db_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT answer_text FROM questions WHERE id = $1",
                        __import__("uuid").UUID(q["question_id"]),
                    )
                    q["expected_answer"] = row["answer_text"] if row else ""

        # Trim to question_count
        questions_for_interview = questions_for_interview[:question_count]

        # Create interview + answers in transaction
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                interview_id = await create_mock_interview(
                    conn, topic, difficulty, duration_minutes
                )
                answer_rows = []
                for i, q in enumerate(questions_for_interview, start=1):
                    answer_rows.append({
                        "question_id": q["question_id"],
                        "question_text": q["question_text"],
                        "expected_answer": q["expected_answer"],
                        "question_order": i,
                    })
                await insert_interview_answers(conn, interview_id, answer_rows)

        first_q = questions_for_interview[0] if questions_for_interview else None
        return {
            "interview_id": interview_id,
            "topic": topic,
            "difficulty": difficulty,
            "duration_minutes": duration_minutes,
            "total_questions": len(questions_for_interview),
            "first_question": {
                "question_id": first_q["question_id"],
                "question_text": first_q["question_text"],
                "question_order": 1,
            } if first_q else None,
        }

    async def evaluate_interview_answer(
        self, interview_id: str, question_order: int, user_answer: str
    ) -> dict:
        answer_row = await get_interview_answer(self.db_pool, interview_id, question_order)
        if not answer_row:
            raise ValueError(f"Answer not found for interview {interview_id}, order {question_order}")

        # LLM evaluation
        prompt_template = _load_prompt("interview_answer_evaluation.txt")
        prompt = prompt_template.format(
            question=answer_row["question_text"],
            expected_answer=answer_row["expected_answer"],
            user_answer=user_answer,
        )

        response = await self.openai.responses.parse(
            model=MODEL_MINI,
            instructions=prompt,
            input=f"Evaluate this interview answer.",
            text_format=InterviewAnswerEvaluation,
            temperature=0.2,
            max_output_tokens=500,
        )
        evaluation = response.output_parsed

        # Update answer row
        await update_interview_answer(
            self.db_pool,
            str(answer_row["id"]),
            user_answer=user_answer,
            score=evaluation.score,
            feedback=evaluation.feedback,
            follow_up_asked=evaluation.needs_follow_up,
        )

        # Get next question
        next_answer = await get_interview_answer(
            self.db_pool, interview_id, question_order + 1
        )

        result: dict = {
            "score": evaluation.score,
            "feedback": evaluation.feedback,
            "follow_up_question": evaluation.follow_up_question if evaluation.needs_follow_up else None,
            "done": next_answer is None and not evaluation.needs_follow_up,
        }

        if next_answer and not evaluation.needs_follow_up:
            result["next_question"] = {
                "question_id": str(next_answer["question_id"]) if next_answer["question_id"] else None,
                "question_text": next_answer["question_text"],
                "question_order": next_answer["question_order"],
            }
        elif not evaluation.needs_follow_up:
            result["next_question"] = None

        return result

    async def evaluate_follow_up(
        self, interview_id: str, question_order: int, follow_up_answer: str
    ) -> dict:
        answer_row = await get_interview_answer(self.db_pool, interview_id, question_order)
        if not answer_row:
            raise ValueError("Answer not found")

        # Simple LLM evaluation for follow-up
        response = await self.openai.responses.create(
            model=MODEL_MINI,
            instructions="Evaluate this follow-up answer briefly. Provide feedback in 1-2 sentences.",
            input=(
                f"Original question: {answer_row['question_text']}\n"
                f"Follow-up answer: <user_input>{follow_up_answer}</user_input>"
            ),
            temperature=0.2,
            max_output_tokens=200,
        )
        follow_up_feedback = response.output_text

        await update_interview_answer(
            self.db_pool,
            str(answer_row["id"]),
            follow_up_answer=follow_up_answer,
            follow_up_feedback=follow_up_feedback,
        )

        # Next question
        next_answer = await get_interview_answer(
            self.db_pool, interview_id, question_order + 1
        )

        result: dict = {
            "follow_up_feedback": follow_up_feedback,
            "done": next_answer is None,
        }
        if next_answer:
            result["next_question"] = {
                "question_id": str(next_answer["question_id"]) if next_answer["question_id"] else None,
                "question_text": next_answer["question_text"],
                "question_order": next_answer["question_order"],
            }
        else:
            result["next_question"] = None

        return result

    async def complete_interview(self, interview_id: str) -> dict:
        detail = await get_interview_detail(self.db_pool, interview_id)
        if not detail:
            raise ValueError("Interview not found")
        if detail["status"] == "completed":
            raise ValueError("Interview already completed")

        answers = detail.get("answers", [])
        scored = [a for a in answers if a.get("score") is not None]
        if not scored:
            raise ValueError("No answers to score")

        # Calculate stats
        total = len(scored)
        scores = [a["score"] for a in scored]
        overall_score = sum(scores) / len(scores) if scores else 0.0
        correct_count = sum(1 for s in scores if s >= 4)
        partial_count = sum(1 for s in scores if s == 3)
        wrong_count = sum(1 for s in scores if s <= 2)

        # LLM summary
        qa_pairs = [
            {
                "question": a["question_text"],
                "answer": a.get("user_answer", ""),
                "score": a.get("score", 0),
                "feedback": a.get("feedback", ""),
            }
            for a in scored
        ]
        prompt_template = _load_prompt("interview_summary.txt")
        prompt = prompt_template.format(
            topic=detail["topic"],
            difficulty=detail["difficulty"],
            duration_minutes=detail["duration_minutes"],
            qa_pairs_json=json.dumps(qa_pairs, indent=2),
        )

        response = await self.openai.responses.parse(
            model=MODEL_MINI,
            instructions=prompt,
            input="Generate the interview summary.",
            text_format=InterviewSummaryLLM,
            temperature=0.3,
            max_output_tokens=800,
        )
        summary = response.output_parsed

        # Finalize in DB
        await complete_mock_interview(
            self.db_pool,
            interview_id,
            overall_score=round(overall_score, 2),
            strengths=summary.strengths,
            weaknesses=summary.weaknesses,
            improvement_tips=summary.improvement_tips,
            total_questions=total,
            correct_count=correct_count,
            partial_count=partial_count,
            wrong_count=wrong_count,
        )

        duration_seconds = None
        if detail.get("started_at"):
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            started = detail["started_at"]
            if hasattr(started, "timestamp"):
                duration_seconds = int(now.timestamp() - started.timestamp())

        return {
            "interview_id": interview_id,
            "topic": detail["topic"],
            "difficulty": detail["difficulty"],
            "overall_score": round(overall_score, 2),
            "total_questions": total,
            "correct_count": correct_count,
            "partial_count": partial_count,
            "wrong_count": wrong_count,
            "strengths": summary.strengths,
            "weaknesses": summary.weaknesses,
            "improvement_tips": summary.improvement_tips,
            "answers": qa_pairs,
            "duration_seconds": duration_seconds,
        }

    async def list_interviews(
        self, topic: str | None, limit: int, offset: int
    ) -> dict:
        return await list_mock_interviews(self.db_pool, topic, limit, offset)

    async def get_interview_summary(self, interview_id: str) -> dict:
        detail = await get_interview_detail(self.db_pool, interview_id)
        if not detail:
            raise ValueError("Interview not found")

        duration_seconds = None
        if detail.get("started_at") and detail.get("completed_at"):
            started = detail["started_at"]
            completed = detail["completed_at"]
            if hasattr(started, "timestamp") and hasattr(completed, "timestamp"):
                duration_seconds = int(completed.timestamp() - started.timestamp())

        strengths = detail.get("strengths") or []
        weaknesses = detail.get("weaknesses") or []
        tips = detail.get("improvement_tips") or []
        if isinstance(strengths, str):
            strengths = json.loads(strengths)
        if isinstance(weaknesses, str):
            weaknesses = json.loads(weaknesses)
        if isinstance(tips, str):
            tips = json.loads(tips)

        return {
            "interview_id": str(detail["id"]),
            "topic": detail["topic"],
            "difficulty": detail["difficulty"],
            "overall_score": detail.get("overall_score") or 0.0,
            "total_questions": detail.get("total_questions") or 0,
            "correct_count": detail.get("correct_count") or 0,
            "partial_count": detail.get("partial_count") or 0,
            "wrong_count": detail.get("wrong_count") or 0,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "improvement_tips": tips,
            "answers": [
                {
                    "question_text": a["question_text"],
                    "user_answer": a.get("user_answer", ""),
                    "score": a.get("score"),
                    "feedback": a.get("feedback", ""),
                }
                for a in detail.get("answers", [])
            ],
            "duration_seconds": duration_seconds,
        }

    async def _generate_questions(
        self, topic: str, difficulty: str, count: int
    ) -> list[dict]:
        prompt_template = _load_prompt("interview_question_generation.txt")
        prompt = prompt_template.format(topic=topic, difficulty=difficulty, count=count)

        response = await self.openai.responses.parse(
            model=MODEL_NANO,
            instructions=prompt,
            input=f"Generate {count} {difficulty} interview questions on {topic}.",
            text_format=GeneratedInterviewQuestions,
            temperature=0.5,
            max_output_tokens=2000,
        )
        result = response.output_parsed
        return [
            {
                "question_text": q.question_text,
                "expected_answer": q.expected_answer,
                "follow_up": q.follow_up,
            }
            for q in result.questions
        ]
