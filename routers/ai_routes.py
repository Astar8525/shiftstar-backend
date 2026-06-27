from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
import models
import httpx
import os

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/chat")
async def ai_chat(
    request: dict,
    current_user: models.User = Depends(get_current_user)
):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="AI not configured")

    prompt = request.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt required")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30.0
            )
        data = response.json()
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"AI error: {data}")
        text = data.get("content", [{}])[0].get("text", "No response")
        return {"response": text}
    except httpx.TimeoutException:
        raise HTTPException(status_code=500, detail="AI request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))