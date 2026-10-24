"""Response data model"""

from typing import List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.model import BaseTableModel
from app.core.base.types import PydanticType
from app.features.response.types import ResponseAnswer


class Response(BaseTableModel):
    __tablename__ = "responses"

    answers: Mapped[List[ResponseAnswer]] = mapped_column(
        PydanticType(List[ResponseAnswer]), nullable=False
    )

    form: Mapped["Form"] = relationship(back_populates="responses")  # noqa: F821
    form_id: Mapped[str] = mapped_column(ForeignKey("forms.id"))

    updated_at = None
