"""Action item endpoints."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ActionItem
from app.schemas import ActionItemOut, ActionItemUpdate

router = APIRouter()

VALID_STATUSES = {"open", "in_progress", "done", "cancelled"}


@router.get("/", response_model=List[ActionItemOut])
def list_action_items(
    owner: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    meeting_id: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(ActionItem)
    if owner:
        q = q.filter(ActionItem.owner.ilike(f"%{owner}%"))
    if status:
        q = q.filter(ActionItem.status == status)
    if meeting_id:
        q = q.filter(ActionItem.meeting_id == meeting_id)
    return q.order_by(ActionItem.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{action_id}", response_model=ActionItemOut)
def get_action_item(action_id: str, db: Session = Depends(get_db)):
    item = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")
    return item


@router.patch("/{action_id}", response_model=ActionItemOut)
def update_action_item(
    action_id: str,
    payload: ActionItemUpdate,
    db: Session = Depends(get_db),
):
    item = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    if payload.status is not None:
        if payload.status not in VALID_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}",
            )
        item.status = payload.status

    if payload.owner is not None:
        item.owner = payload.owner

    if payload.due_date is not None:
        item.due_date = payload.due_date

    db.commit()
    db.refresh(item)
    return item
