from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.model import BaseTableModel


class UserGoogleToken(BaseTableModel):
    """A refresh token authorizing a Formbrew user to export to their Google Drive."""

    __tablename__ = "user_google_tokens"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), unique=True, index=True, nullable=False
    )
    google_refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    google_email: Mapped[Optional[str]] = mapped_column(String)

    updated_at = None

    def __str__(self) -> str:
        return f"UserGoogleToken(user_id={self.user_id}, google_email={self.google_email})"
