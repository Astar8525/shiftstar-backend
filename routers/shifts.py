from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from auth import get_current_user
import models
import schemas

router = APIRouter(prefix="/shifts", tags=["shifts"])

@router.get("/", response_model=List[schemas.ShiftOut])
def get_shifts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.Shift).filter(
        models.Shift.company_id == current_user.company_id
    ).all()

@router.post("/", response_model=schemas.ShiftOut)
def create_shift(
    shift: schemas.ShiftCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    new_shift = models.Shift(
        company_id=current_user.company_id,
        name=shift.name,
        start_time=shift.start_time,
        end_time=shift.end_time
    )
    db.add(new_shift)
    db.commit()
    db.refresh(new_shift)
    return new_shift

@router.put("/{shift_id}", response_model=schemas.ShiftOut)
def update_shift(
    shift_id: int,
    shift_data: schemas.ShiftUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    shift = db.query(models.Shift).filter(
        models.Shift.id == shift_id,
        models.Shift.company_id == current_user.company_id
    ).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    if shift_data.name is not None:
        shift.name = shift_data.name
    if shift_data.start_time is not None:
        shift.start_time = shift_data.start_time
    if shift_data.end_time is not None:
        shift.end_time = shift_data.end_time
    db.commit()
    db.refresh(shift)
    return shift

@router.delete("/{shift_id}")
def delete_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    shift = db.query(models.Shift).filter(
        models.Shift.id == shift_id,
        models.Shift.company_id == current_user.company_id
    ).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    db.delete(shift)
    db.commit()
    return {"message": "Shift deleted"}