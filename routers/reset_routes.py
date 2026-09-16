from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import hash_password
import models
import secrets
import time

router = APIRouter(prefix="/reset", tags=["reset"])

# Simple in-memory token store — works for now
reset_tokens = {}

@router.post("/request")
def request_reset(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        # Don't reveal if email exists
        return {"message": "If that email is registered you will receive a reset link"}
    
    token = secrets.token_urlsafe(32)
    reset_tokens[token] = {"user_id": user.id, "expires": time.time() + 3600}
    
    reset_url = f"https://web-production-f21c8.up.railway.app/dashboard?reset_token={token}"
    
    # Log to console until email is set up
    print(f"PASSWORD RESET REQUEST: {email} -> {reset_url}")
    
    return {"message": "If that email is registered you will receive a reset link"}

@router.post("/confirm")
def confirm_reset(payload: dict, db: Session = Depends(get_db)):
    token = payload.get("token", "")
    new_password = payload.get("password", "")
    
    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and password required")
    
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    token_data = reset_tokens.get(token)
    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    
    if time.time() > token_data["expires"]:
        del reset_tokens[token]
        raise HTTPException(status_code=400, detail="Reset link has expired. Please request a new one.")
    
    user = db.query(models.User).filter(models.User.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    
    user.password_hash = hash_password(new_password)
    db.commit()
    
    del reset_tokens[token]
    
    return {"message": "Password updated successfully"}