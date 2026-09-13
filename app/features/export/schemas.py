from typing import Optional

from pydantic import BaseModel, Field

from app.core.base.schema import BaseResponseModel


class GoogleTokenExchangeRequest(BaseModel):
    code: str = Field(min_length=1)
    code_verifier: str = Field(min_length=43, max_length=128)


class GoogleExportStatus(BaseModel):
    connected: bool
    google_email: Optional[str] = None


class GoogleStatusResponse(BaseResponseModel):
    data: GoogleExportStatus


class GoogleConnectData(BaseModel):
    connected: bool
    google_email: Optional[str] = None


class GoogleConnectResponse(BaseResponseModel):
    data: GoogleConnectData


class GoogleSheetsExportData(BaseModel):
    spreadsheet_url: str


class GoogleSheetsExportResponse(BaseResponseModel):
    data: GoogleSheetsExportData


class GoogleDisconnectResponse(BaseResponseModel):
    pass
