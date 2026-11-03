from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import UUID

from fastapi import Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AnonymousSession, UserPreference


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def get_or_create_session(
    request: Request, response: Response, db: Session
) -> tuple[AnonymousSession, UserPreference]:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    now = datetime.now(timezone.utc)
    session = None
    if token:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        session = db.scalar(
            select(AnonymousSession).where(AnonymousSession.token_hash == token_hash)
        )
        if session is not None and _as_utc(session.expires_at) <= now:
            db.execute(
                delete(UserPreference).where(UserPreference.session_id == session.id)
            )
            db.delete(session)
            db.flush()
            session = None
    if session is None:
        token = secrets.token_urlsafe(32)
        session = AnonymousSession(
            token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(days=settings.session_ttl_days),
        )
        db.add(session)
        db.flush()
    else:
        session.last_seen_at = now
        session.expires_at = now + timedelta(days=settings.session_ttl_days)
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        path="/",
    )
    preference = db.get(UserPreference, session.id)
    if preference is None:
        preference = UserPreference(session_id=session.id)
        db.add(preference)
        db.flush()
    return session, preference
