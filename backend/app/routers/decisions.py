"""Decision endpoints."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Decision
from app.schemas import DecisionOut

router = APIRouter()


@router.get("/", response_model=List[DecisionOut])
def list_decisions(
    meeting_id: Optional[str] = Query(None),
    made_by: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(Decision)
    if meeting_id:
        q = q.filter(Decision.meeting_id == meeting_id)
    if made_by:
        q = q.filter(Decision.made_by.ilike(f"%{made_by}%"))
    return q.order_by(Decision.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{decision_id}", response_model=DecisionOut)
def get_decision(decision_id: str, db: Session = Depends(get_db)):
    item = db.query(Decision).filter(Decision.id == decision_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Decision not found")
    return item
