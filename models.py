from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    users = relationship("User", back_populates="company")
    shifts = relationship("Shift", back_populates="company")
    events = relationship("Event", back_populates="company")
    production_data = relationship("ProductionData", back_populates="company")
    shift_history = relationship("ShiftHistory", back_populates="company")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="supervisor")  # supervisor, manager, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    company = relationship("Company", back_populates="users")
    events = relationship("Event", back_populates="user")

class Shift(Base):
    __tablename__ = "shifts"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    name = Column(String)
    start_time = Column(String)
    end_time = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    company = relationship("Company", back_populates="shifts")

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    shift_name = Column(String)
    machine = Column(String)
    cause = Column(String)
    event_type = Column(String)
    duration = Column(Integer)
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    company = relationship("Company", back_populates="events")
    user = relationship("User", back_populates="events")

class ProductionData(Base):
    __tablename__ = "production_data"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    shift_name = Column(String)
    date = Column(String)
    units_produced = Column(Float)
    units_defect = Column(Float)
    planned_time_min = Column(Float)
    downtime_min = Column(Float, nullable=True)
    ideal_cycle_sec = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    company = relationship("Company", back_populates="production_data")

class ShiftHistory(Base):
    __tablename__ = "shift_history"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    shift_name = Column(String)
    date = Column(String)
    oee = Column(Float)
    good_units = Column(Float)
    defects = Column(Float)
    total_downtime = Column(Integer)
    cause_totals_json = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    company = relationship("Company", back_populates="shift_history")