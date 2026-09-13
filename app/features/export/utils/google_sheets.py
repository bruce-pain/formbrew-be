"""Google Sheets API helpers for the export feature.

Creates a spreadsheet in the user's Drive and populates it with rows.
Takes the plaintext refresh token from the caller (the service decrypts
the stored token first), so this module stays stateless — no DB here.
Google failures propagate for the service layer to map to HTTP responses.
"""

import logging
from typing import Any, List

from google.auth.transport import requests as google_requests
from googleapiclient.discovery import build

from app.features.export.utils import google_oauth

logger = logging.getLogger(__name__)


def _sheets_service(credentials: Any):
    try:
        credentials.refresh(google_requests.Request())
    except Exception as exc:  # noqa: BLE001 - surface as a friendly 409 upstream
        logger.warning("Token refresh failed: %s", exc)
        raise
    return build("sheets", "v4", credentials=credentials)


def create_spreadsheet_with_rows(
    refresh_token: str, title: str, rows: List[List[str]]
) -> str:
    """Create a spreadsheet in the user's Drive and populate cells from rows.

    Returns the https://docs.google.com/spreadsheets/d/... URL.
    """
    service = _sheets_service(
        google_oauth.credentials_from_refresh_token(refresh_token)
    )
    num_rows = max(len(rows), 1)
    num_cols = max((len(rows[0]) if rows else 1), 1)

    spreadsheet = (
        service.spreadsheets()
        .create(
            body={
                "properties": {"title": title},
                "sheets": [
                    {
                        "properties": {
                            "gridProperties": {
                                "rowCount": num_rows,
                                "columnCount": num_cols,
                            }
                        }
                    }
                ],
            },
            fields="spreadsheetUrl,spreadsheetId",
        )
        .execute()
    )

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet["spreadsheetId"],
        range="Sheet1!A1",
        valueInputOption="USER_ENTERED",
        body={"values": rows},
    ).execute()

    logger.info(
        "Created spreadsheet %s with %d rows", spreadsheet["spreadsheetUrl"], len(rows)
    )
    return spreadsheet["spreadsheetUrl"]
