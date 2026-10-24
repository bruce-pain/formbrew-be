"""Form data model"""

from typing import List, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base.model import BaseTableModel
from app.core.base.types import PydanticType
from app.features.form.types import FormQuestion


class Form(BaseTableModel):
    __tablename__ = "forms"

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str]

    # define questions field with custom PydanticType
    questions: Mapped[Optional[List[FormQuestion]]] = mapped_column(
        PydanticType(List[FormQuestion]), nullable=True
    )

    is_published: Mapped[bool] = mapped_column(default=False)

    conversation_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default=None
    )

    # Define many to one relationship with user
    user: Mapped["User"] = relationship(back_populates="forms")  # noqa: F821
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))

    responses: Mapped[List["Response"]] = relationship(back_populates="form")  # noqa: F821

    def __str__(self) -> str:
        return "Form: {} - [{}]".format(self.title, self.id)
