"""Response export routes (Google Sheets + CSV)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies.security import get_current_user
from app.core.limiter import limiter
from app.features.auth.models import User
from app.features.export import schemas
from app.features.export.service import ExportService

export_google_router = APIRouter(prefix="/export/google", tags=["Google Export"])


@export_google_router.post(
    path="/tokens",
    status_code=status.HTTP_200_OK,
    response_model=schemas.GoogleConnectResponse,
    summary="Connect Google Sheets",
    description="Exchange the OAuth code for a refresh token and store it for this user",
)
@limiter.limit("10/minute")
def connect_google_sheets(
    request: Request,  # required by slowapi — do not remove
    schema: schemas.GoogleTokenExchangeRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    service = ExportService(db=db)
    data = service.connect_google(
        user_id=current_user.id,
        code=schema.code,
        code_verifier=schema.code_verifier,
        redirect_uri=schema.redirect_uri,
    )
    return schemas.GoogleConnectResponse(
        status_code=status.HTTP_200_OK, message="Google Sheets connected", data=data
    )


@export_google_router.get(
    path="/status",
    status_code=status.HTTP_200_OK,
    response_model=schemas.GoogleConnectionStatusResponse,
    summary="Google Sheets connection status",
    description="Checks the database only — no Google network call",
)
def get_google_export_status(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    service = ExportService(db=db)
    data = service.get_google_status(user_id=current_user.id)
    return schemas.GoogleConnectionStatusResponse(
        status_code=status.HTTP_200_OK, message="Status retrieved", data=data
    )


@export_google_router.post(
    path="/sheets/{form_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.GoogleSheetsExportResponse,
    summary="Export a form's responses to Google Sheets",
    description="Build rows from the form's responses and create a spreadsheet in the user's Drive",
)
def export_form_to_google_sheets(
    form_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    service = ExportService(db=db)
    data = service.export_responses_to_sheets(user_id=current_user.id, form_id=form_id)
    return schemas.GoogleSheetsExportResponse(
        status_code=status.HTTP_200_OK,
        message="Responses exported to Google Sheets",
        data=data,
    )


@export_google_router.post(
    path="/disconnect",
    status_code=status.HTTP_200_OK,
    response_model=schemas.GoogleDisconnectResponse,
    summary="Disconnect Google Sheets",
    description="Forgets the stored token locally (does not revoke it on Google)",
)
def disconnect_google_sheets(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    service = ExportService(db=db)
    service.disconnect_google(user_id=current_user.id)
    return schemas.GoogleDisconnectResponse(
        status_code=status.HTTP_200_OK, message="Google Sheets disconnected"
    )


export_csv_router = APIRouter(prefix="/export/csv", tags=["CSV Export"])


@export_csv_router.get(
    path="/{form_id}",
    status_code=status.HTTP_200_OK,
    summary="Export form responses as CSV",
    description="Download the form's responses as a CSV file (Excel and Sheets compatible)",
)
def export_form_to_csv(
    form_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    service = ExportService(db=db)
    content, filename = service.export_responses_to_csv(
        user_id=current_user.id, form_id=form_id
    )
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
