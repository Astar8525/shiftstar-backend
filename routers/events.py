from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from auth import get_current_user
import models
import schemas

router = APIRouter(prefix="/events", tags=["events"])

@router.get("/", response_model=List[schemas.EventOut])
def get_events(
    shift_name: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Event).filter(
        models.Event.company_id == current_user.company_id
    )
    if shift_name:
        query = query.filter(models.Event.shift_name == shift_name)
    if date:
        query = query.filter(
            models.Event.timestamp.like(f"{date}%")
        )
    return query.order_by(models.Event.timestamp.desc()).all()

@router.post("/", response_model=schemas.EventOut)
def create_event(
    event: schemas.EventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    new_event = models.Event(
        company_id=current_user.company_id,
        user_id=current_user.id,
        shift_name=event.shift_name,
        machine=event.machine,
        cause=event.cause,
        event_type=event.event_type,
        duration=event.duration,
        notes=event.notes,
        timestamp=event.timestamp
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event

@router.delete("/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    event = db.query(models.Event).filter(
        models.Event.id == event_id,
        models.Event.company_id == current_user.company_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()
    return {"message": "Event deleted"}