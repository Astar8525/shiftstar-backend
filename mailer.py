import os
import json
import urllib.request
import urllib.error


def send_email(to, subject, text, html=None):
    """Send one email through Resend. Returns (ok, detail). Never prints or returns secrets."""
    key = (os.getenv("RESEND_API_KEY") or "").strip()
    if not key:
        return False, "no api key configured"
    sender = (os.getenv("EMAIL_FROM") or "ShiftStar <noreply@getshiftstar.com>").strip()
    recipients = [to] if isinstance(to, str) else list(to)
    payload = {"from": sender, "to": recipients, "subject": subject, "text": text}
    if html:
        payload["html"] = html
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "User-Agent": "shiftstar/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return True, resp.status
    except urllib.error.HTTPError as err:
        try:
            detail = err.read().decode("utf-8", "replace")[:300]
        except Exception:
            detail = ""
        return False, "HTTP %s %s" % (err.code, detail)
    except Exception as err:
        return False, type(err).__name__