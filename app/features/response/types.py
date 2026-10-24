"""Response answer data structures (embedded in responses.answers JSONB)."""

from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ResponseAnswerBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: Annotated[str, Field(min_length=1)]


class TextAnswer(ResponseAnswerBase):
    answer_type: Literal["text"] = "text"
    value: Optional[str] = None


class SelectAnswer(ResponseAnswerBase):
    answer_type: Literal["select"] = "select"
    selected_option: Optional[str] = None


class CheckboxAnswer(ResponseAnswerBase):
    answer_type: Literal["checkbox"] = "checkbox"
    selected_options: Optional[List[str]] = None


ResponseAnswer = Annotated[
    Union[TextAnswer, SelectAnswer, CheckboxAnswer], Field(discriminator="answer_type")
]
