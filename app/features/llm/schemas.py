from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.core.base.schema import BaseResponseModel
from app.features.form.types import FormQuestion


class FormResponse(BaseModel):
    title: Optional[str]
    description: Optional[str]
    questions: List[FormQuestion]


class SetTitleInstruction(BaseModel):
    op: Literal["set_title"] = "set_title"
    title: str


class SetDescriptionInstruction(BaseModel):
    op: Literal["set_description"] = "set_description"
    description: str


class AddQuestionInstruction(BaseModel):
    op: Literal["add_question"] = "add_question"
    question: FormQuestion
    after_id: Optional[str] = None


class UpdateQuestionInstruction(BaseModel):
    op: Literal["update_question"] = "update_question"
    question_id: str
    question: FormQuestion


class RemoveQuestionInstruction(BaseModel):
    op: Literal["remove_question"] = "remove_question"
    question_id: str


class ReorderQuestionsInstruction(BaseModel):
    op: Literal["reorder_questions"] = "reorder_questions"
    question_ids: List[str]


FormInstruction = Annotated[
    Union[
        SetTitleInstruction,
        SetDescriptionInstruction,
        AddQuestionInstruction,
        UpdateQuestionInstruction,
        RemoveQuestionInstruction,
        ReorderQuestionsInstruction,
    ],
    Field(discriminator="op"),
]


class InstructionBatch(BaseModel):
    instructions: List[FormInstruction]


class LLMRequest(BaseModel):
    prompt: str
    conversation_id: Optional[str] = None
    current_state: Optional[FormResponse] = None


class LLMResponse(BaseResponseModel):
    data: FormResponse
    conversation_id: str
