"""Google OAuth helpers for the Sheets export feature.

Covers the "hybrid" Authorization Code + PKCE flow: exchanging the
frontend-obtained one-time code for credentials, reading the connected
account's email from the id_token, and rebuilding usable credentials
from a stored refresh token. No DB or HTTPException logic here.
"""

from typing import Any, Dict

from google.auth.transport import requests as google_requests
from google.oauth2 import credentials as google_credentials
from google.oauth2 import id_token as google_id_token
from google_auth_oauthlib.flow import Flow

from app.core.config import settings

# Scopes requested at consent. Must EXACTLY match what the frontend requests
# when it builds the consent URL, and what the Cloud console allows.
# openid + email let us read the user's address from the id_token.
# spreadsheets + drive.file let us create a spreadsheet in the user's Drive,
# restricted to files we create.
SCOPES = [
    "openid",
    "email",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

TOKEN_URI = "https://oauth2.googleapis.com/token"


def _client_config(redirect_uri: str) -> Dict[str, Any]:
    """The subset of an OAuth client descriptor our Flow needs."""
    return {
        "web": {
            # The redirect already happened client-side (on the frontend);
            # this must match the authorization request's redirect_uri.
            "redirect_uris": [redirect_uri],
            "client_id": settings.GOOGLE_SHEETS_CLIENT_ID,
            "client_secret": settings.GOOGLE_SHEETS_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": TOKEN_URI,
        }
    }


def exchange_code(code: str, code_verifier: str, redirect_uri: str) -> dict:
    """Exchange the one-time authorization code for credentials.

    Returns a dict with 'refresh_token', 'access_token' and 'id_token'.
    Raises OAuthError/HttpError on invalid codes.
    """
    flow = Flow.from_client_config(_client_config(redirect_uri), scopes=SCOPES)
    flow.redirect_uri = redirect_uri
    flow.fetch_token(code=code, code_verifier=code_verifier)
    credentials = flow.credentials
    # NOTE: refresh_token may be absent if offline access was not granted.
    # Treat as empty defensively; the service layer rejects it with a 400.
    return {
        "refresh_token": credentials.refresh_token or "",
        "access_token": credentials.token or "",
        "id_token": credentials.id_token or "",
    }


def get_id_token_email(id_token_string: str) -> str:
    """Verify the id_token and return the user's Google email address.

    Lenient by design: the email is display-only (the Formbrew JWT already
    identifies the user), so no email_verified check.
    """
    idinfo = google_id_token.verify_oauth2_token(
        id_token_string,
        google_requests.Request(),
        settings.GOOGLE_SHEETS_CLIENT_ID,
    )
    return idinfo["email"]


def credentials_from_refresh_token(refresh_token: str) -> Any:
    """Build usable credentials from a stored refresh token."""
    return google_credentials.Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=settings.GOOGLE_SHEETS_CLIENT_ID,
        client_secret=settings.GOOGLE_SHEETS_CLIENT_SECRET,
        scopes=SCOPES,
    )
