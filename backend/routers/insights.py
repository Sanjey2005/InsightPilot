"""
Insights router — Phase 3.

  GET  /insights/{id}           Full insight detail: narrative, chart, SQL, data, feedback summary
  POST /insights/{id}/feedback  Submit thumbs_up | thumbs_down | saved (upserts per user+insight)
"""
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_current_user
from core.database import get_db
from models.insight import Insight
from models.insight_feedback import InsightFeedback
from models.run import Run
from models.user import User

router = APIRouter()

FeedbackSignal = Literal["thumbs_up", "thumbs_down", "saved"]

VALID_SIGNALS = {"thumbs_up", "thumbs_down", "saved"}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    signal: FeedbackSignal
    note: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    insight_id: str
    signal: str
    note: Optional[str] = None
    created_at: datetime


class FeedbackSummary(BaseModel):
    thumbs_up: int
    thumbs_down: int
    saved: int
    user_signal: Optional[str] = None   # current user's signal, if any


class InsightDetailResponse(BaseModel):
    id: str
    run_id: str
    user_id: str
    type: str
    title: str
    narrative: str
    sql_used: Optional[str] = None
    chart_config: Optional[Dict[str, Any]] = None
    data: Optional[List[Dict[str, Any]]] = None
    kpi_column: Optional[str] = None
    severity: str
    created_at: datetime
    feedback: FeedbackSummary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_owned_insight(insight_id: str, user_id: str, db: Session) -> Insight:
    """Fetch insight and verify ownership, raising 404 on miss or access violation."""
    ins = db.query(Insight).filter(Insight.id == insight_id).first()
    if not ins:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found.")
    if ins.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found.")
    return ins


def _feedback_summary(insight_id: str, user_id: str, db: Session) -> FeedbackSummary:
    rows = db.query(InsightFeedback).filter(InsightFeedback.insight_id == insight_id).all()
    counts: Dict[str, int] = {"thumbs_up": 0, "thumbs_down": 0, "saved": 0}
    user_signal: Optional[str] = None
    for row in rows:
        if row.signal in counts:
            counts[row.signal] += 1
        if row.user_id == user_id:
            user_signal = row.signal
    return FeedbackSummary(**counts, user_signal=user_signal)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/{insight_id}",
    response_model=InsightDetailResponse,
    summary="Full insight detail: narrative, chart config, raw SQL, data, and feedback counts.",
)
def get_insight(
    insight_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InsightDetailResponse:
    ins = _get_owned_insight(insight_id, current_user.id, db)
    feedback = _feedback_summary(insight_id, current_user.id, db)

    return InsightDetailResponse(
        id=ins.id,
        run_id=ins.run_id,
        user_id=ins.user_id,
        type=ins.type,
        title=ins.title,
        narrative=ins.narrative,
        sql_used=ins.sql_used,
        chart_config=json.loads(ins.chart_config) if ins.chart_config else None,
        data=json.loads(ins.data_json) if ins.data_json else None,
        kpi_column=ins.kpi_column,
        severity=ins.severity,
        created_at=ins.created_at,
        feedback=feedback,
    )


@router.post(
    "/{insight_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit thumbs_up, thumbs_down, or saved for an insight. Upserts per user.",
)
def submit_feedback(
    insight_id: str,
    body: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    # Verify the insight exists and belongs to the user
    _get_owned_insight(insight_id, current_user.id, db)

    # Upsert: one feedback row per user+insight combination (last signal wins)
    existing = (
        db.query(InsightFeedback)
        .filter(
            InsightFeedback.insight_id == insight_id,
            InsightFeedback.user_id == current_user.id,
        )
        .first()
    )

    if existing:
        existing.signal = body.signal
        existing.note = body.note
        existing.created_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        record = existing
    else:
        record = InsightFeedback(
            id=str(uuid.uuid4()),
            insight_id=insight_id,
            user_id=current_user.id,
            signal=body.signal,
            note=body.note,
            created_at=datetime.utcnow(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return FeedbackResponse(
        id=record.id,
        insight_id=record.insight_id,
        signal=record.signal,
        note=record.note,
        created_at=record.created_at,
    )
