"""Response request/response schemas"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict

from app.core.base.schema import BaseResponseModel
from app.features.response.types import ResponseAnswer


class FormResponseCreateRequest(BaseModel):
    answers: List[ResponseAnswer]


class FormResponseData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    answers: List[ResponseAnswer]
    form_id: str
    created_at: datetime


class FormResponseResponse(BaseResponseModel):
    data: FormResponseData


class FormResponseListResponse(BaseResponseModel):
    data: List[FormResponseData]
