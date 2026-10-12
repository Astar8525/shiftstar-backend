import os
import html
import httpx
from datetime import datetime


def send_signup_alert(name, email, company, role):
    """Email the owner when someone registers. Never raises."""
    key = os.environ.get("RESEND_API_KEY")
    to = os.environ.get("NOTIFY_EMAIL")
    if not key or not to:
        print("Signup alert skipped: RESEND_API_KEY or NOTIFY_EMAIL is not set")
        return
    esc = lambda v: html.escape(str(v))
    body = (
        "<h2>New ShiftStar signup</h2>"
        "<p><b>Name:</b> " + esc(name) + "<br>"
        "<b>Email:</b> " + esc(email) + "<br>"
        "<b>Company:</b> " + esc(company) + "<br>"
        "<b>Role:</b> " + esc(role) + "<br>"
        "<b>Time (UTC):</b> " + datetime.utcnow().strftime("%Y-%m-%d %H:%M") + "</p>"
    )
    try:
        r = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": "Bearer " + key},
            json={
                "from": "ShiftStar <onboarding@resend.dev>",
                "to": [to],
                "subject": "New ShiftStar signup: " + str(name)[:80],
                "html": body,
            },
            timeout=10,
        )
        if r.status_code >= 300:
            print("Signup alert failed:", r.status_code, r.text[:200])
        else:
            print("Signup alert sent")
    except Exception as e:
        print("Signup alert error:", e)