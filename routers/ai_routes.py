import os
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
import models

router = APIRouter(prefix="/ai", tags=["ai"])

# AI requests allowed per company per day (UTC), by plan
DAILY_LIMITS = {"starter": 10, "pro": 50, "team": 200, "plant": 500}
MAX_PROMPT_CHARS = 20000

# Reply languages the dashboard can ask for (everything else stays English)
LANG_NAMES = {
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Brazilian Portuguese",
    "zh": "Simplified Chinese",
    "ja": "Japanese",
}


def _refund(db, usage):
    try:
        usage.count = max(0, (usage.count or 0) - 1)
        db.commit()
    except Exception:
        db.rollback()


@router.post("/chat")
async def ai_chat(
    request: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="AI not configured")

    prompt = request.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt required")
    if not isinstance(prompt, str) or len(prompt) > MAX_PROMPT_CHARS:
        raise HTTPException(status_code=400, detail="Prompt is too long")

    lang = request.get("lang")
    lang_name = LANG_NAMES.get(lang) if isinstance(lang, str) else None

    company = db.query(models.Company).filter(models.Company.id == current_user.company_id).first()
    plan = ((company.plan if company is not None else None) or "starter").lower()
    limit = DAILY_LIMITS.get(plan, DAILY_LIMITS["starter"])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    usage = db.query(models.AIUsage).filter(
        models.AIUsage.company_id == current_user.company_id,
        models.AIUsage.day == today
    ).first()
    if usage is None:
        usage = models.AIUsage(company_id=current_user.company_id, day=today, count=0)
        db.add(usage)
        db.flush()
    if usage.count >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily AI limit reached ({limit} requests per day on the {plan.capitalize()} plan). Upgrade for more, or try again tomorrow."
        )
    usage.count += 1
    db.commit()

    body = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    }
    if lang_name:
        body["system"] = (
            "You are ShiftStar AI. Always write your entire reply in " + lang_name +
            ", even if the question or the data below is in English. "
            "Keep technical abbreviations such as OEE, SAP and MRP unchanged."
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json=body,
                timeout=30.0
            )
        data = response.json()
        if response.status_code != 200:
            print("AI upstream error", response.status_code, data)
            _refund(db, usage)
            raise HTTPException(status_code=500, detail="The AI service had a problem. Please try again.")
        text = data.get("content", [{}])[0].get("text", "No response")
        return {"response": text}
    except HTTPException:
        raise
    except httpx.TimeoutException:
        _refund(db, usage)
        raise HTTPException(status_code=500, detail="AI request timed out")
    except Exception as e:
        print("AI error", repr(e))
        _refund(db, usage)
        raise HTTPException(status_code=500, detail="AI request failed. Please try again.")