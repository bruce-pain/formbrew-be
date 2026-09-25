"""Form question data structures (embedded in forms.questions JSONB)."""

from typing import Annotated, List, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class FormQuestionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Annotated[str, Field(min_length=1)]
    text: Annotated[str, Field(min_length=1, max_length=500)]
    required: bool


class TextQuestion(FormQuestionBase):
    answer_type: Literal["text"] = "text"


class SelectQuestion(FormQuestionBase):
    answer_type: Literal["select"] = "select"
    options: Annotated[List[str], Field(min_length=1)]


class CheckboxQuestion(FormQuestionBase):
    answer_type: Literal["checkbox"] = "checkbox"
    options: Annotated[List[str], Field(min_length=1)]


FormQuestion = Annotated[
    Union[TextQuestion, SelectQuestion, CheckboxQuestion],
    Field(discriminator="answer_type"),
]
