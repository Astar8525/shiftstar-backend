import os
import html
import time
import httpx
from datetime import datetime

LAST = {"when": None, "status": "no signup alert has run since this deploy"}
_last_test = 0.0


def _cfg():
    key = (os.environ.get("RESEND_API_KEY") or "").strip()
    to = (os.environ.get("NOTIFY_EMAIL") or "").strip()
    return key, to


def _send(subject, body_html):
    key, to = _cfg()
    if not key or not to:
        return "skipped: RESEND_API_KEY set=%s, NOTIFY_EMAIL set=%s" % (bool(key), bool(to))
    try:
        r = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": "Bearer " + key},
            json={
                "from": "ShiftStar <onboarding@resend.dev>",
                "to": [to],
                "subject": subject,
                "html": body_html,
            },
            timeout=10,
        )
        if r.status_code >= 300:
            return "failed: %s %s" % (r.status_code, r.text[:200])
        return "sent (status %s)" % r.status_code
    except Exception as e:
        return "error: %s" % e


def send_signup_alert(name, email, company, role):
    """Email the owner when someone registers. Never raises."""
    try:
        esc = lambda v: html.escape(str(v))
        body = (
            "<h2>New ShiftStar signup</h2>"
            "<p><b>Name:</b> " + esc(name) + "<br>"
            "<b>Email:</b> " + esc(email) + "<br>"
            "<b>Company:</b> " + esc(company) + "<br>"
            "<b>Role:</b> " + esc(role) + "<br>"
            "<b>Time (UTC):</b> " + datetime.utcnow().strftime("%Y-%m-%d %H:%M") + "</p>"
        )
        result = _send("New ShiftStar signup: " + str(name)[:80], body)
    except Exception as e:
        result = "error: %s" % e
    LAST["when"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    LAST["status"] = result
    print("Signup alert", result, flush=True)


def alert_check():
    global _last_test
    key, to = _cfg()
    out = {
        "key_set": bool(key),
        "key_length": len(key),
        "key_starts_with_re_": key.startswith("re_"),
        "notify_email_set": bool(to),
        "last_signup_alert": dict(LAST),
    }
    now = time.time()
    if now - _last_test < 60:
        out["test_send"] = "skipped: wait 60 seconds between tests"
    else:
        _last_test = now
        out["test_send"] = _send("ShiftStar alert test", "<p>This is a test of the signup alert.</p>")
    return out