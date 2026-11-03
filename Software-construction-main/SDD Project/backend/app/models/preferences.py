from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnonymousSession(Base):
    __tablename__ = "anonymous_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("anonymous_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="SET NULL")
    )
    preference_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="default")
    primary_metric: Mapped[str] = mapped_column(String(32), nullable=False, default="calories")
    primary_direction: Mapped[str] = mapped_column(String(8), nullable=False, default="least")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint("preference_mode IN ('default', 'custom')", name="ck_preference_mode"),
        CheckConstraint(
            "primary_metric IN ('calories', 'carbohydrates', 'protein', 'fat', 'fibre', 'price')",
            name="ck_preference_metric",
        ),
        CheckConstraint("primary_direction IN ('most', 'least')", name="ck_preference_direction"),
    )
