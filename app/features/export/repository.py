from typing import Optional

from sqlalchemy.orm import Session

from app.core.base.repository import BaseRepository
from app.features.export.models import UserGoogleToken


class GoogleExportTokenRepository(BaseRepository[UserGoogleToken]):
    def __init__(self, db: Session):
        super().__init__(UserGoogleToken, db)

    def get_by_user(self, user_id: str) -> Optional[UserGoogleToken]:
        return (
            self.db.query(self.model)
            .filter(self.model.user_id == user_id)
            .first()
        )

    def upsert_token(
        self,
        user_id: str,
        refresh_token: str,
        google_email: str,
    ) -> UserGoogleToken:
        """Create-or-replace the token row for a user (one row per user)."""
        token_row = self.get_by_user(user_id)
        if token_row is None:
            token_row = UserGoogleToken(
                user_id=user_id,
                google_refresh_token=refresh_token,
                google_email=google_email,
            )
            self.db.add(token_row)
        else:
            token_row.google_refresh_token = refresh_token
            token_row.google_email = google_email
        self.db.commit()
        self.db.refresh(token_row)
        return token_row

    def delete_for_user(self, user_id: str) -> bool:
        token_row = self.get_by_user(user_id)
        if token_row is None:
            return False
        self.db.delete(token_row)
        self.db.commit()
        return True
