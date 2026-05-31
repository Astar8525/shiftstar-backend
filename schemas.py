from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ── Company ──
class CompanyCreate(BaseModel):
    name: str

class CompanyOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

# ── Auth ──
class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    company_name: str
    role: Optional[str] = "supervisor"

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    company_id: int
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

# ── Shifts ──
class ShiftCreate(BaseModel):
    name: str
    start_time: str
    end_time: str

class ShiftUpdate(BaseModel):
    name: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]

class ShiftOut(BaseModel):
    id: int
    name: str
    start_time: str
    end_time: str
    class Config:
        from_attributes = True

# ── Events ──
class EventCreate(BaseModel):
    shift_name: str
    machine: str
    cause: str
    event_type: str
    duration: int
    notes: Optional[str] = None
    timestamp: datetime

class EventOut(BaseModel):
    id: int
    shift_name: str
    machine: str
    cause: str
    event_type: str
    duration: int
    notes: Optional[str]
    timestamp: datetime
    user_id: int
    class Config:
        from_attributes = True

# ── Production ──
class ProductionCreate(BaseModel):
    shift_name: str
    date: str
    units_produced: float
    units_defect: float
    planned_time_min: float
    downtime_min: Optional[float] = None
    ideal_cycle_sec: Optional[float] = None

class ProductionOut(BaseModel):
    id: int
    shift_name: str
    date: str
    units_produced: float
    units_defect: float
    planned_time_min: float
    downtime_min: Optional[float]
    ideal_cycle_sec: Optional[float]
    class Config:
        from_attributes = True

# ── Shift History ──
class ShiftHistoryCreate(BaseModel):
    shift_name: str
    date: str
    oee: float
    good_units: float
    defects: float
    total_downtime: int
    cause_totals_json: str

class ShiftHistoryOut(BaseModel):
    id: int
    shift_name: str
    date: str
    oee: float
    good_units: float
    defects: float
    total_downtime: int
    cause_totals_json: str
    class Config:
        from_attributes = True