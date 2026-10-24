"""Response service"""

from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.features.form.repository import FormRepository
from app.features.form.types import CheckboxQuestion, FormQuestion, SelectQuestion
from app.features.response import schemas
from app.features.response.models import Response
from app.features.response.repository import ResponseRepository
from app.features.response.types import (
    CheckboxAnswer,
    ResponseAnswer,
    SelectAnswer,
    TextAnswer,
)


def _is_answer_empty(answer: ResponseAnswer) -> bool:
    match answer:
        case TextAnswer():
            return answer.value is None or len(answer.value) < 1
        case SelectAnswer():
            return answer.selected_option is None or len(answer.selected_option) < 1
        case CheckboxAnswer():
            return answer.selected_options is None or len(answer.selected_options) < 1


class ResponseService:
    def __init__(self, db: Session):
        self.repository = ResponseRepository(db)
        self.form_repository = FormRepository(db)

    @staticmethod
    def _validate_answers(
        form_questions: List[FormQuestion], answers: List[ResponseAnswer]
    ) -> List[ResponseAnswer]:
        logger.info(
            "Validating %d answers against %d form questions",
            len(answers),
            len(form_questions),
        )

        def http_422_error(detail: str) -> None:
            """reusable function to throw 422 exception responses"""
            logger.warning("Answer validation failed: %s", detail)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
            )

        # create a map of questions with their id as the key
        form_questions_dict: dict[str, FormQuestion] = {}

        # use this later to check if required questions were answered
        required_question_ids: List[str] = []
        answered_question_ids: List[str] = []
        missing_required_question_ids: List[str] = []

        for question in form_questions:
            form_questions_dict[question.id] = question

            if question.required:
                required_question_ids.append(question.id)

        # checks to be performed per answer
        for answer in answers:
            question_id = answer.question_id

            # check if the question_id exists
            if question_id not in form_questions_dict:
                http_422_error(
                    detail="Answer references unknown question '{}'".format(question_id)
                )

            answer_question = form_questions_dict[question_id]

            # check if the answer_type matches the question's answer type
            if answer.answer_type != answer_question.answer_type:
                http_422_error(
                    detail="Invalid answer type for question '{}': expected '{}', got '{}'".format(
                        question_id, answer_question.answer_type, answer.answer_type
                    )
                )

            # check required questions have non-empty answers
            if answer_question.required and _is_answer_empty(answer):
                http_422_error(
                    detail="Question '{}' is required but answer is empty".format(
                        question_id
                    )
                )

            # for select/checkbox answers, validate that the selected option(s)
            # belong to the question's options

            match answer, answer_question:
                case SelectAnswer() as a, SelectQuestion() as q:
                    if (
                        a.selected_option is not None
                        and a.selected_option not in q.options
                    ):
                        http_422_error(
                            "Invalid option '{}' for question '{}': expected one of [{}]".format(
                                answer.selected_option,
                                question_id,
                                ", ".join(answer_question.options),
                            )
                        )

                case CheckboxAnswer() as a, CheckboxQuestion() as q:
                    if a.selected_options:
                        for option in a.selected_options:
                            if option not in q.options:
                                http_422_error(
                                    "Invalid option '{}' for question '{}': expected one of [{}]".format(
                                        option,
                                        question_id,
                                        ", ".join(q.options),
                                    )
                                )

            answered_question_ids.append(question_id)

        # check required questions
        for question in required_question_ids:
            if question not in answered_question_ids:
                missing_required_question_ids.append(question)

        if len(missing_required_question_ids) > 0:
            http_422_error(
                detail="Required questions left unanswered: {}".format(
                    ", ".join(missing_required_question_ids)
                )
            )

        logger.info("Answer validation passed for %d answers", len(answers))
        return answers

    def submit(
        self, form_id: str, schema: schemas.FormResponseCreateRequest
    ) -> Response:
        logger.info("Submitting response for form: %s", form_id)

        form = self.form_repository.get_public_form(form_id)
        if not form or not form.questions:
            logger.warning("Form not found or not published | id: %s", form_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Form not found or not published",
            )

        validated_answers = self._validate_answers(
            form_questions=form.questions,
            answers=schema.answers,
        )

        response = Response(form_id=form_id, answers=validated_answers)
        created = self.repository.create(response)
        logger.info(
            "Response submitted successfully | id: %s | form: %s", created.id, form_id
        )
        return created

    def get_form_responses(self, form_id: str, user_id: str) -> list[Response]:
        logger.info("Fetching responses for form: %s | user: %s", form_id, user_id)
        form = self.form_repository.get_user_form(user_id, form_id)
        if not form:
            logger.warning("Form not found | id: %s | user: %s", form_id, user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Form not found",
            )
        responses = self.repository.get_by_form(form.id)
        logger.info("Retrieved %d responses for form: %s", len(responses), form.id)
        return responses

    def get_form_response(
        self, form_id: str, response_id: str, user_id: str
    ) -> Response:
        logger.info(
            "Fetching response | id: %s | form: %s | user: %s",
            response_id,
            form_id,
            user_id,
        )
        form = self.form_repository.get_user_form(user_id, form_id)
        if not form:
            logger.warning("Form not found | id: %s | user: %s", form_id, user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Form not found",
            )
        response = self.repository.get_form_response(form.id, response_id)
        if not response:
            logger.warning(
                "Response not found | id: %s | form: %s", response_id, form.id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Response not found",
            )
        logger.info(
            "Response retrieved successfully | id: %s | form: %s", response_id, form.id
        )
        return response
