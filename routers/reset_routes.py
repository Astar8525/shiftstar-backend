import os
import html as _html
import hashlib
import secrets
import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from auth import hash_password
from mailer import send_email
import models

router = APIRouter(prefix="/reset", tags=["reset"])

APP_BASE_URL = (os.getenv("APP_BASE_URL") or "https://web-production-f21c8.up.railway.app").rstrip("/")
TOKEN_TTL_MINUTES = 60
MAX_REQUESTS_PER_HOUR = 3
MIN_PASSWORD_LEN = 8
MAX_PASSWORD_LEN = 128
GENERIC_OK = {"message": "If that email is registered you will receive a reset link"}

TEXTS = {
    "en": {
        "subject": "Reset your ShiftStar password",
        "intro": "We received a request to reset the password for your ShiftStar account. Use the link below to choose a new password.",
        "button": "Reset password",
        "note": "This link works once and expires in 1 hour. If you didn't ask for this, you can ignore this email - your password won't change.",
    },
    "es": {
        "subject": "Restablece tu contrase\u00f1a de ShiftStar",
        "intro": "Recibimos una solicitud para restablecer la contrase\u00f1a de tu cuenta de ShiftStar. Usa el siguiente enlace para elegir una nueva contrase\u00f1a.",
        "button": "Restablecer contrase\u00f1a",
        "note": "Este enlace funciona una sola vez y caduca en 1 hora. Si no lo solicitaste, puedes ignorar este correo: tu contrase\u00f1a no cambiar\u00e1.",
    },
    "fr": {
        "subject": "R\u00e9initialisez votre mot de passe ShiftStar",
        "intro": "Nous avons re\u00e7u une demande de r\u00e9initialisation du mot de passe de votre compte ShiftStar. Utilisez le lien ci-dessous pour choisir un nouveau mot de passe.",
        "button": "R\u00e9initialiser le mot de passe",
        "note": "Ce lien ne fonctionne qu'une seule fois et expire dans 1 heure. Si vous n'\u00eates pas \u00e0 l'origine de cette demande, ignorez cet e-mail : votre mot de passe ne changera pas.",
    },
    "de": {
        "subject": "Setzen Sie Ihr ShiftStar-Passwort zur\u00fcck",
        "intro": "Wir haben eine Anfrage erhalten, das Passwort f\u00fcr Ihr ShiftStar-Konto zur\u00fcckzusetzen. Verwenden Sie den folgenden Link, um ein neues Passwort festzulegen.",
        "button": "Passwort zur\u00fccksetzen",
        "note": "Dieser Link funktioniert nur einmal und l\u00e4uft in 1 Stunde ab. Wenn Sie dies nicht angefordert haben, k\u00f6nnen Sie diese E-Mail ignorieren \u2013 Ihr Passwort bleibt unver\u00e4ndert.",
    },
    "pt": {
        "subject": "Redefina sua senha do ShiftStar",
        "intro": "Recebemos uma solicita\u00e7\u00e3o para redefinir a senha da sua conta do ShiftStar. Use o link abaixo para escolher uma nova senha.",
        "button": "Redefinir senha",
        "note": "Este link funciona apenas uma vez e expira em 1 hora. Se voc\u00ea n\u00e3o fez essa solicita\u00e7\u00e3o, ignore este e-mail \u2013 sua senha n\u00e3o ser\u00e1 alterada.",
    },
    "zh": {
        "subject": "\u91cd\u7f6e\u60a8\u7684 ShiftStar \u5bc6\u7801",
        "intro": "\u6211\u4eec\u6536\u5230\u4e86\u91cd\u7f6e\u60a8 ShiftStar \u8d26\u6237\u5bc6\u7801\u7684\u8bf7\u6c42\u3002\u8bf7\u4f7f\u7528\u4e0b\u65b9\u94fe\u63a5\u8bbe\u7f6e\u65b0\u5bc6\u7801\u3002",
        "button": "\u91cd\u7f6e\u5bc6\u7801",
        "note": "\u6b64\u94fe\u63a5\u4ec5\u53ef\u4f7f\u7528\u4e00\u6b21\uff0c1 \u5c0f\u65f6\u540e\u5931\u6548\u3002\u5982\u679c\u8fd9\u4e0d\u662f\u60a8\u672c\u4eba\u7684\u64cd\u4f5c\uff0c\u8bf7\u5ffd\u7565\u6b64\u90ae\u4ef6\uff0c\u60a8\u7684\u5bc6\u7801\u4e0d\u4f1a\u6539\u53d8\u3002",
    },
    "ja": {
        "subject": "ShiftStar \u306e\u30d1\u30b9\u30ef\u30fc\u30c9\u3092\u30ea\u30bb\u30c3\u30c8",
        "intro": "ShiftStar \u30a2\u30ab\u30a6\u30f3\u30c8\u306e\u30d1\u30b9\u30ef\u30fc\u30c9\u30ea\u30bb\u30c3\u30c8\u306e\u30ea\u30af\u30a8\u30b9\u30c8\u3092\u53d7\u3051\u4ed8\u3051\u307e\u3057\u305f\u3002\u4e0b\u306e\u30ea\u30f3\u30af\u304b\u3089\u65b0\u3057\u3044\u30d1\u30b9\u30ef\u30fc\u30c9\u3092\u8a2d\u5b9a\u3057\u3066\u304f\u3060\u3055\u3044\u3002",
        "button": "\u30d1\u30b9\u30ef\u30fc\u30c9\u3092\u30ea\u30bb\u30c3\u30c8",
        "note": "\u3053\u306e\u30ea\u30f3\u30af\u306f 1 \u56de\u3060\u3051\u6709\u52b9\u3067\u3001 1 \u6642\u9593\u5f8c\u306b\u7121\u52b9\u306b\u306a\u308a\u307e\u3059\u3002\u5fc3\u5f53\u305f\u308a\u304c\u306a\u3044\u5834\u5408\u306f\u3001\u3053\u306e\u30e1\u30fc\u30eb\u3092\u7121\u8996\u3057\u3066\u304f\u3060\u3055\u3044\u3002\u30d1\u30b9\u30ef\u30fc\u30c9\u306f\u5909\u66f4\u3055\u308c\u307e\u305b\u3093\u3002",
    },
}


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def _hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _pick_lang(chosen, accept_header):
    candidates = [chosen or ""] + [part.split(";")[0] for part in (accept_header or "").split(",")]
    for cand in candidates:
        code = cand.strip().lower()[:2]
        if code in TEXTS:
            return code
    return "en"


def _send_reset_email(to, link, lang):
    t = TEXTS.get(lang, TEXTS["en"])
    text = t["intro"] + "\n\n" + link + "\n\n" + t["note"] + "\n\nShiftStar"
    body = (
        '<div style="font-family:Arial,Helvetica,sans-serif;max-width:480px;margin:0 auto;color:#222">'
        + "<p>" + _html.escape(t["intro"]) + "</p>"
        + '<p><a href="' + link + '" style="display:inline-block;background:#4f46e5;color:#fff;'
        + 'text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:bold">'
        + _html.escape(t["button"]) + "</a></p>"
        + '<p style="color:#666;font-size:13px">' + _html.escape(t["note"]) + "</p>"
        + '<p style="color:#666;font-size:13px">ShiftStar</p></div>'
    )
    ok, detail = send_email(to, t["subject"], text, body)
    if not ok:
        print("reset email failed:", detail)


@router.post("/request")
def request_reset(payload: dict, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    user = db.query(models.User).filter(func.lower(models.User.email) == email).first()
    if not user or user.is_active is False:
        return GENERIC_OK

    now = _utcnow()
    recent = db.query(models.PasswordReset).filter(
        models.PasswordReset.user_id == user.id,
        models.PasswordReset.created_at >= now - datetime.timedelta(hours=1),
    ).count()
    if recent >= MAX_REQUESTS_PER_HOUR:
        return GENERIC_OK

    db.query(models.PasswordReset).filter(
        models.PasswordReset.user_id == user.id,
        models.PasswordReset.used_at.is_(None),
    ).update({models.PasswordReset.used_at: now}, synchronize_session=False)

    token = secrets.token_urlsafe(32)
    db.add(models.PasswordReset(
        user_id=user.id,
        token_hash=_hash(token),
        expires_at=now + datetime.timedelta(minutes=TOKEN_TTL_MINUTES),
    ))
    db.commit()

    link = APP_BASE_URL + "/dashboard?reset_token=" + token
    lang = _pick_lang(payload.get("lang"), request.headers.get("accept-language"))
    background_tasks.add_task(_send_reset_email, user.email, link, lang)
    return GENERIC_OK


@router.post("/confirm")
def confirm_reset(payload: dict, db: Session = Depends(get_db)):
    token = (payload.get("token") or "").strip()
    new_password = payload.get("password") or ""

    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and password required")
    if len(new_password) < MIN_PASSWORD_LEN:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if len(new_password) > MAX_PASSWORD_LEN:
        raise HTTPException(status_code=400, detail="Password is too long")

    row = db.query(models.PasswordReset).filter(models.PasswordReset.token_hash == _hash(token)).first()
    if not row or row.used_at is not None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=datetime.timezone.utc)
    if _utcnow() > expires:
        raise HTTPException(status_code=400, detail="Reset link has expired. Please request a new one.")

    user = db.query(models.User).filter(models.User.id == row.user_id).first()
    if not user or user.is_active is False:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    user.password_hash = hash_password(new_password)
    row.used_at = _utcnow()
    db.commit()

    return {"message": "Password updated successfully"}