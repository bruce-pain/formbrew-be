"""Form request/response schemas"""

from datetime import datetime
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.base.schema import BaseResponseModel
from app.features.form.types import FormQuestion


class FormCreateRequest(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=255)]
    description: Annotated[str, Field(max_length=2000)]
    questions: Optional[List[FormQuestion]] = Field(default=None, min_length=1)
    conversation_id: Optional[str] = None


class FormUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    questions: Optional[List[FormQuestion]] = Field(default=None, min_length=1)
    is_published: Optional[bool] = None


class FormResponseData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    questions: Optional[List[FormQuestion]]
    is_published: bool
    conversation_id: Optional[str]
    user_id: str
    created_at: datetime
    updated_at: datetime


class FormResponse(BaseResponseModel):
    data: FormResponseData


class FormListResponseData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    is_published: bool
    user_id: str
    created_at: datetime
    updated_at: datetime


class FormListResponse(BaseResponseModel):
    data: List[FormListResponseData]
