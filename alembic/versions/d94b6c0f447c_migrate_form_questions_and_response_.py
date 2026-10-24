"""migrate form questions and response answers to discriminated unions

Data-only revision (no DDL — columns stay JSONB). Transforms persisted rows
from the flat question/answer shapes into the discriminated-union shapes:

- forms.questions[]:
    - text question: drop answer_select_options / answer_select_multiple.
    - select question: answer_select_options -> options; the old
      answer_select_multiple flag decides the new answer_type
      (True -> "checkbox", otherwise -> "select"); drop both old keys.
- responses.answers[]:
    - text answer: text_answer -> value.
    - select answer: typed by the parent form's question multiplicity —
      single-select -> answer_type "select" with scalar selected_option
      (None and [] both canonicalize to None — both mean "empty"),
      multi-select -> answer_type "checkbox" with list selected_options.

Deliberately bypasses the ORM and PydanticType: PydanticType validates reads
against the NEW unions (extra="forbid"), so old rows cannot be loaded through
the app models. All I/O here is raw SQL with explicit JSON serialization.

Corrupt data aborts the migration loudly instead of being silently coerced:
- answer referencing an unknown question_id,
- single-select answer holding 2+ items in select_answer,
- select question with missing/empty answer_select_options.

Revision ID: d94b6c0f447c
Revises: b32cbbde39b9
Create Date: 2026-09-25 11:36:49.063077

"""

import json
from typing import Any, Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d94b6c0f447c"
down_revision: Union[str, None] = "b32cbbde39b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BATCH_SIZE = 1000


def _as_list(value: Any) -> Any:
    """psycopg may hand back JSONB as parsed objects or as text; normalize."""
    if value is None:
        return None
    if isinstance(value, str):
        return json.loads(value)
    return value


# ---------------------------------------------------------------------------
# upgrade transforms (old shape -> discriminated unions)
# ---------------------------------------------------------------------------


def _upgrade_question(question: dict, form_id: str) -> dict:
    base = {
        "id": question["id"],
        "text": question["text"],
        "required": question["required"],
    }
    answer_type = question.get("answer_type")
    if answer_type == "text":
        return {**base, "answer_type": "text"}
    if answer_type == "select":
        options = question.get("answer_select_options")
        if not options:
            raise RuntimeError(
                f"forms[{form_id}]: select question "
                f"'{base['id']}' has missing/empty answer_select_options"
            )
        new_type = (
            "checkbox" if question.get("answer_select_multiple") is True else "select"
        )
        return {**base, "answer_type": new_type, "options": options}
    raise RuntimeError(
        f"forms[{form_id}]: question '{base['id']}' "
        f"has unknown answer_type {answer_type!r}"
    )


def _upgrade_answer(
    answer: dict, multiplicity: dict, response_id: str, form_id: str
) -> dict:
    question_id = answer["question_id"]
    answer_type = answer.get("answer_type")
    if answer_type == "text":
        return {
            "question_id": question_id,
            "answer_type": "text",
            "value": answer.get("text_answer"),
        }
    if answer_type == "select":
        selected = answer.get("select_answer")
        if selected is not None and not isinstance(selected, list):
            raise RuntimeError(
                f"responses[{response_id}]: answer to question "
                f"'{question_id}' has non-list select_answer {selected!r}"
            )
        if question_id not in multiplicity:
            # Orphaned answer - form questions missing or question deleted.
            # Infer multiplicity from the shape of the old select_answer.
            if selected is None or len(selected) == 0:
                return {
                    "question_id": question_id,
                    "answer_type": "select",
                    "selected_option": None,
                }
            if len(selected) == 1:
                return {
                    "question_id": question_id,
                    "answer_type": "select",
                    "selected_option": selected[0],
                }
            return {
                "question_id": question_id,
                "answer_type": "checkbox",
                "selected_options": selected,
            }
        if multiplicity[question_id]:
            return {
                "question_id": question_id,
                "answer_type": "checkbox",
                "selected_options": selected,
            }
        if selected is None or len(selected) == 0:
            option = None
        elif len(selected) == 1:
            option = selected[0]
        else:
            raise RuntimeError(
                f"responses[{response_id}]: single-select answer to question "
                f"'{question_id}' holds {len(selected)} items in select_answer"
            )
        return {
            "question_id": question_id,
            "answer_type": "select",
            "selected_option": option,
        }
    raise RuntimeError(
        f"responses[{response_id}]: answer to question '{question_id}' "
        f"has unknown answer_type {answer_type!r}"
    )


# ---------------------------------------------------------------------------
# downgrade transforms (discriminated unions -> old shape)
# ---------------------------------------------------------------------------


def _downgrade_question(question: dict, form_id: str) -> dict:
    base = {
        "id": question["id"],
        "text": question["text"],
        "required": question["required"],
    }
    answer_type = question.get("answer_type")
    if answer_type == "text":
        return {
            **base,
            "answer_type": "text",
            "answer_select_options": None,
            "answer_select_multiple": None,
        }
    if answer_type in ("select", "checkbox"):
        return {
            **base,
            "answer_type": "select",
            "answer_select_options": question.get("options"),
            "answer_select_multiple": answer_type == "checkbox",
        }
    raise RuntimeError(
        f"forms[{form_id}]: question '{base['id']}' "
        f"has unknown answer_type {answer_type!r}"
    )


def _downgrade_answer(
    answer: dict, question_types: dict, response_id: str, form_id: str
) -> dict:
    question_id = answer["question_id"]
    answer_type = answer.get("answer_type")
    if answer_type == "text":
        return {
            "question_id": question_id,
            "answer_type": "text",
            "text_answer": answer.get("value"),
            "select_answer": None,
        }
    if question_id not in question_types:
        raise RuntimeError(
            f"responses[{response_id}]: answer references unknown "
            f"question_id '{question_id}' (form {form_id})"
        )
    if answer_type == "select":
        option = answer.get("selected_option")
        return {
            "question_id": question_id,
            "answer_type": "select",
            "text_answer": None,
            "select_answer": None if option is None else [option],
        }
    if answer_type == "checkbox":
        return {
            "question_id": question_id,
            "answer_type": "select",
            "text_answer": None,
            "select_answer": answer.get("selected_options"),
        }
    raise RuntimeError(
        f"responses[{response_id}]: answer to question '{question_id}' "
        f"has unknown answer_type {answer_type!r}"
    )


# ---------------------------------------------------------------------------
# batched row helpers
# ---------------------------------------------------------------------------


def _update_forms(connection: sa.Connection, transform) -> dict:
    """Rewrite forms.questions in batches; return {form_id: {qid: is_multi}}."""
    form_multiplicity: dict = {}
    offset = 0
    update_stmt = sa.text(
        "UPDATE forms SET questions = CAST(:q AS JSONB) WHERE id = :id"
    )
    while True:
        rows = (
            connection.execute(
                sa.text(
                    "SELECT id, questions FROM forms "
                    "WHERE questions IS NOT NULL ORDER BY id "
                    "LIMIT :limit OFFSET :offset"
                ),
                {"limit": BATCH_SIZE, "offset": offset},
            )
            .mappings()
            .all()
        )
        if not rows:
            break
        params = []
        for row in rows:
            questions = _as_list(row["questions"])
            if not questions:
                form_multiplicity[row["id"]] = {}
                params.append({"q": json.dumps([]), "id": row["id"]})
                continue
            new_questions = [transform(q, row["id"]) for q in questions]
            params.append({"q": json.dumps(new_questions), "id": row["id"]})
            form_multiplicity[row["id"]] = {
                q["id"]: q.get("answer_select_multiple") is True for q in questions
            }
        if params:
            connection.execute(update_stmt, params)
        offset += BATCH_SIZE
    return form_multiplicity


def _update_responses(connection: sa.Connection, transform, form_lookup: dict) -> None:
    offset = 0
    update_stmt = sa.text(
        "UPDATE responses SET answers = CAST(:a AS JSONB) WHERE id = :id"
    )
    while True:
        rows = (
            connection.execute(
                sa.text(
                    "SELECT id, form_id, answers FROM responses "
                    "ORDER BY id LIMIT :limit OFFSET :offset"
                ),
                {"limit": BATCH_SIZE, "offset": offset},
            )
            .mappings()
            .all()
        )
        if not rows:
            break
        params = []
        for row in rows:
            answers = _as_list(row["answers"])
            form_id = row["form_id"]
            if form_id not in form_lookup:
                # Parent form has NULL questions (or is missing): only text
                # answers can be typed without the join; anything else aborts.
                lookup: dict = {}
            else:
                lookup = form_lookup[form_id]
            new_answers = [transform(a, lookup, row["id"], form_id) for a in answers]
            params.append({"a": json.dumps(new_answers), "id": row["id"]})
        connection.execute(update_stmt, params)
        offset += BATCH_SIZE


def _load_form_new_types(connection: sa.Connection) -> dict:
    """Read {form_id: {question_id: new answer_type}} without modifying rows."""
    form_types: dict = {}
    offset = 0
    while True:
        rows = (
            connection.execute(
                sa.text(
                    "SELECT id, questions FROM forms WHERE questions IS NOT NULL "
                    "ORDER BY id LIMIT :limit OFFSET :offset"
                ),
                {"limit": BATCH_SIZE, "offset": offset},
            )
            .mappings()
            .all()
        )
        if not rows:
            break
        for row in rows:
            form_types[row["id"]] = {
                q["id"]: q.get("answer_type") for q in _as_list(row["questions"])
            }
        offset += BATCH_SIZE
    return form_types


def upgrade() -> None:
    connection = op.get_bind()
    # Forms first: responses are typed by their parent form's questions.
    form_multiplicity = _update_forms(connection, _upgrade_question)
    _update_responses(connection, _upgrade_answer, form_multiplicity)


def downgrade() -> None:
    connection = op.get_bind()
    # Responses first while parent forms still carry the new union shapes,
    # so checkbox answers can be told apart from single-select ones.
    form_types = _load_form_new_types(connection)
    _update_responses(connection, _downgrade_answer, form_types)
    _update_forms(connection, _downgrade_question)
