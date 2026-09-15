"""Export service"""

from typing import List

from cryptography.fernet import InvalidToken
from fastapi import HTTPException, status
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.features.export import schemas
from app.features.export.repository import ExportTokenRepository
from app.features.export.utils import google_oauth, google_sheets
from app.features.export.utils.crypto import decrypt_token, encrypt_token
from app.features.export.utils.csv_export import build_csv_filename, rows_to_csv_bytes
from app.features.form.models import Form
from app.features.form.repository import FormRepository
from app.features.response.models import Response
from app.features.response.repository import ResponseRepository


def build_spreadsheet_title(form: Form) -> str:
    """Spreadsheet title. Keep it short — Sheets has a 100-char title cap."""
    title = form.title.strip()
    suffix = "Responses"
    if len(f"{title} - {suffix}") <= 100:
        return f"{title} - {suffix}"
    # Overhead of the truncated form is len("... - ") + len(suffix).
    return f"{title[: (100 - len(suffix) - 6)]}... - {suffix}"


def build_rows(form: Form, responses: List[Response]) -> List[List[str]]:
    """One row per response, one column per question.

    - Column 1 is the submission time (human-readable, UTC).
    - One column per question, in the form's question order.
    - text answers → the raw text; missing/blank → "".
    - select answers → options joined with ", "; none → "".
    Works for single- and multiple-select alike. Unknown questions → "".
    """
    questions = form.questions or []
    headers = ["Submitted At", *(q.text for q in questions)]
    rows = [headers]

    for response in sorted(responses, key=lambda r: r.created_at):
        answer_map = {a.question_id: a for a in (response.answers or [])}
        row: List[str] = [response.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")]
        for q in questions:
            answer = answer_map.get(q.id)
            if answer is None:
                row.append("")
            elif answer.answer_type == "text":
                row.append((answer.text_answer or "").strip())
            else:
                row.append(", ".join(answer.select_answer or []))
        rows.append(row)

    return rows


class ExportService:
    def __init__(self, db: Session):
        self.db = db
        self.token_repo = ExportTokenRepository(db)
        self.form_repo = FormRepository(db)
        self.response_repo = ResponseRepository(db)

    # ----- connection lifecycle -----

    def get_status(self, user_id: str) -> schemas.GoogleExportStatus:
        token_row = self.token_repo.get_by_user(user_id)
        if token_row is None:
            return schemas.GoogleExportStatus(connected=False, google_email=None)
        return schemas.GoogleExportStatus(
            connected=True, google_email=token_row.google_email
        )

    def connect(
        self, user_id: str, code: str, code_verifier: str, redirect_uri: str
    ) -> schemas.GoogleConnectData:
        try:
            tokens = google_oauth.exchange_code(
                code=code, code_verifier=code_verifier, redirect_uri=redirect_uri
            )
        except Exception as exc:
            logger.warning("Google code exchange failed for user %s: %s", user_id, exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid authorization code. Please try again.",
            ) from exc
        refresh_token = tokens["refresh_token"]
        if not refresh_token:
            # Consent with offline access should always yield one; if not, we
            # can't act later. Surface a clear 400 rather than storing garbage.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google did not return a refresh token. Please reconnect.",
            )
        try:
            google_email = google_oauth.get_id_token_email(tokens["id_token"])
        except Exception as exc:
            logger.warning(
                "Google ID token verification failed for user %s: %s", user_id, exc
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not verify Google account. Please try again.",
            ) from exc
        self.token_repo.upsert_token(
            user_id=user_id,
            refresh_token=encrypt_token(refresh_token),
            google_email=google_email,
        )
        logger.info("Connected Google export for user %s (%s)", user_id, google_email)
        return schemas.GoogleConnectData(connected=True, google_email=google_email)

    def disconnect(self, user_id: str) -> None:
        deleted = self.token_repo.delete_for_user(user_id)
        # Local-only disconnect: we forget the token. We do NOT revoke it on
        # Google's side, so the Spreadsheets the user already owns keep working.
        if deleted:
            logger.info("Disconnected Google export for user %s", user_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No connection to disconnect",
            )

    # ----- csv export -----

    def export_responses_to_csv(self, user_id: str, form_id: str) -> tuple[bytes, str]:
        """Export a form's responses as CSV bytes + download filename.

        Reuses build_rows so columns, ordering and cell formatting match
        the Sheets export. Needs no Google connection.
        """
        form = self.form_repo.get_user_form(user_id, form_id)
        if form is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Form not found"
            )

        responses = self.response_repo.get_by_form(form.id)
        rows = build_rows(form, responses)
        return rows_to_csv_bytes(rows), build_csv_filename(form.title)

    # ----- sheets export -----

    def export_responses_to_sheets(
        self, user_id: str, form_id: str
    ) -> schemas.GoogleSheetsExportData:
        form = self.form_repo.get_user_form(user_id, form_id)
        if form is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Form not found"
            )

        token_row = self.token_repo.get_by_user(user_id)
        if token_row is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Google Sheets is not connected. Connect first.",
            )

        try:
            refresh_token = decrypt_token(token_row.google_refresh_token)
        except InvalidToken:
            # Encryption key changed underneath us (dedicated key rotation).
            logger.exception("Cannot decrypt Google token for user %s", user_id)
            self.token_repo.delete_for_user(user_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Google connection is invalid. Reconnect.",
            ) from None

        responses = self.response_repo.get_by_form(form.id)
        rows = build_rows(form, responses)
        title = build_spreadsheet_title(form)

        try:
            spreadsheet_url = google_sheets.create_spreadsheet_with_rows(
                refresh_token=refresh_token, title=title, rows=rows
            )
        except HttpError as exc:
            status_code = getattr(getattr(exc, "resp", None), "status", None)
            if status_code is not None and 500 <= status_code < 600:
                logger.warning(
                    "Sheets export transient failure for form %s: %s", form_id, exc
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Google Sheets is temporarily unavailable. Try again.",
                ) from exc
            logger.warning("Sheets export failed for form %s: %s", form_id, exc)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Your Google connection has expired. Reconnect Google Sheets.",
            ) from exc
        except Exception as exc:  # covers InvalidGrant, refresh failures
            logger.warning("Sheets export failed for form %s: %s", form_id, exc)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Your Google connection has expired. Reconnect Google Sheets.",
            ) from exc

        return schemas.GoogleSheetsExportData(spreadsheet_url=spreadsheet_url)
