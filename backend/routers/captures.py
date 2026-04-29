"""
Captures router — create, list, detail, and tag endpoints.
"""
import json
import re
import uuid as uuid_module
import csv
import io
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from core.rate_limiter import rate_limit
from models.capture_models import CaptureRequest, CaptureResponse, CaptureListItem, CaptureDetail, FactItem, QuestionItem
from services.capture_service import CaptureService

router = APIRouter()

_TAG_PATTERN = re.compile(r'^[a-zA-Z0-9\-_ ]+$')


class TagUpdateRequest(BaseModel):
    tags: list[str] = Field(..., max_length=20)

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v):
        validated = []
        for tag in v:
            tag = tag.strip()
            if not tag:
                continue
            if len(tag) > 50:
                raise ValueError(f"Tag '{tag[:20]}...' exceeds 50 characters")
            if not _TAG_PATTERN.match(tag):
                raise ValueError(f"Tag '{tag}' contains invalid characters. Only alphanumeric, hyphens, underscores, and spaces are allowed.")
            validated.append(tag)
        return validated


def _sanitize_csv_value(value: str) -> str:
    """Prefix dangerous CSV cell values to prevent formula injection."""
    if value and value[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + value
    return value


@router.post("/", response_model=CaptureResponse, dependencies=[Depends(rate_limit(10))])
async def create_capture(body: CaptureRequest, request: Request):
    """Create a new capture — triggers full extraction + question generation pipeline."""
    service = CaptureService(
        db_pool=request.app.state.db_pool,
        openai_client=request.app.state.openai,
        scheduler=request.app.state.scheduler,
    )
    return await service.process(body)


@router.get("/", response_model=list[CaptureListItem])
async def list_captures(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List recent captures with fact count."""
    from core.db_queries import list_captures as db_list_captures
    rows = await db_list_captures(request.app.state.db_pool, limit, offset)
    return [
        CaptureListItem(
            id=str(r["id"]),
            raw_text=r["raw_text"][:200],
            source_type=r["source_type"],
            facts_count=r["facts_count"],
            tags=list(r.get("tags", [])),
            created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


@router.get("/tags")
async def get_all_tags(request: Request):
    """List all tags with usage counts."""
    from core.db_queries import list_all_tags
    return await list_all_tags(request.app.state.db_pool)


@router.get("/export/json", dependencies=[Depends(rate_limit(2, 60))])
async def export_json(request: Request):
    """Export all captures with facts and questions as JSON."""
    from core.db_queries import bulk_export_captures
    rows = await bulk_export_captures(request.app.state.db_pool)

    # Group rows by capture
    captures_map: dict = {}
    for r in rows:
        cid = str(r["capture_id"])
        if cid not in captures_map:
            captures_map[cid] = {
                "id": cid,
                "raw_text": r["raw_text"],
                "source_type": r["source_type"],
                "why_it_matters": r.get("why_it_matters"),
                "tags": list(r.get("tags", [])) if r.get("tags") else [],
                "created_at": r["created_at"].isoformat(),
                "facts": {},
                "questions": {},
            }
        entry = captures_map[cid]
        if r.get("fact_id") and str(r["fact_id"]) not in entry["facts"]:
            entry["facts"][str(r["fact_id"])] = {
                "content": r["fact_content"],
                "content_type": r["fact_content_type"],
            }
        if r.get("question_id") and str(r["question_id"]) not in entry["questions"]:
            entry["questions"][str(r["question_id"])] = {
                "question_text": r["question_text"],
                "answer_text": r["answer_text"],
                "question_type": r["question_type"],
            }

    results = []
    for entry in captures_map.values():
        entry["facts"] = list(entry["facts"].values())
        entry["questions"] = list(entry["questions"].values())
        results.append(entry)

    content = json.dumps(results, indent=2, ensure_ascii=False)
    return StreamingResponse(
        io.StringIO(content),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=recall-export.json"},
    )


@router.get("/export/csv", dependencies=[Depends(rate_limit(2, 60))])
async def export_csv(request: Request):
    """Export all captures with facts as CSV."""
    from core.db_queries import bulk_export_captures
    rows = await bulk_export_captures(request.app.state.db_pool)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["capture_id", "source_type", "tags", "created_at", "raw_text", "fact", "question", "answer"])

    seen_rows: set = set()
    for r in rows:
        cid = str(r["capture_id"])
        source_type = r["source_type"]
        tags_str = _sanitize_csv_value(", ".join(r.get("tags", []) or []))
        created = r["created_at"].isoformat()
        raw = _sanitize_csv_value(r["raw_text"])

        if r.get("fact_id"):
            key = (cid, "fact", str(r["fact_id"]))
            if key not in seen_rows:
                seen_rows.add(key)
                writer.writerow([
                    cid, source_type, tags_str, created, raw,
                    _sanitize_csv_value(r["fact_content"]), "", "",
                ])
        elif r.get("question_id"):
            key = (cid, "question", str(r["question_id"]))
            if key not in seen_rows:
                seen_rows.add(key)
                writer.writerow([
                    cid, source_type, tags_str, created, "",
                    "", _sanitize_csv_value(r["question_text"]),
                    _sanitize_csv_value(r["answer_text"]),
                ])
        else:
            key = (cid, "empty", "")
            if key not in seen_rows:
                seen_rows.add(key)
                writer.writerow([cid, source_type, tags_str, created, raw, "", "", ""])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=recall-export.csv"},
    )


@router.get("/{capture_id}", response_model=CaptureDetail)
async def get_capture(capture_id: str, request: Request):
    """Get a capture with its extracted facts and generated questions."""
    try:
        uuid_module.UUID(capture_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid capture ID format")
    from core.db_queries import get_capture_detail
    result = await get_capture_detail(request.app.state.db_pool, capture_id)
    if not result:
        raise HTTPException(status_code=404, detail="Capture not found")

    c = result["capture"]
    return CaptureDetail(
        id=str(c["id"]),
        raw_text=c["raw_text"],
        source_type=c["source_type"],
        why_it_matters=c.get("why_it_matters"),
        tags=result.get("tags", []),
        created_at=c["created_at"].isoformat(),
        facts=[
            FactItem(
                id=str(f["id"]),
                content=f["content"],
                content_type=f["content_type"],
                created_at=f["created_at"].isoformat(),
            )
            for f in result["facts"]
        ],
        questions=[
            QuestionItem(
                id=str(q["id"]),
                question_text=q["question_text"],
                answer_text=q["answer_text"],
                question_type=q["question_type"],
                technique_used=q.get("technique_used"),
                mnemonic_hint=q.get("mnemonic_hint"),
                state=q["state"],
                due=q["due"].isoformat(),
            )
            for q in result["questions"]
        ],
    )


@router.put("/{capture_id}/tags")
async def update_capture_tags(capture_id: str, body: TagUpdateRequest, request: Request):
    """Set tags for a capture (replaces existing tags)."""
    try:
        uid = uuid_module.UUID(capture_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid capture ID format")
    # Verify capture exists
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM captures WHERE id = $1)", uid)
    if not exists:
        raise HTTPException(status_code=404, detail="Capture not found")
    from core.db_queries import set_capture_tags
    tags = await set_capture_tags(pool, capture_id, body.tags)
    return {"tags": tags}
