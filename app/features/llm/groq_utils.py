"""Groq utils"""

import json
from typing import List, Optional

from groq import AsyncGroq
from groq.types.chat import (
    ChatCompletionMessage,
    ChatCompletionMessageParam,
)

from app.features.llm.schemas import InstructionBatch

GROQ_MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """
    You are an expert at designing forms for data collection.

    You receive the current form state (title, description, and questions)
    and a user instruction. Generate a list of editing operations that modify
    the form to satisfy the user's instruction.

    Available operations:
    - set_title: Set the form title.
    - set_description: Set the form description.
    - add_question: Add a new question. Provide the full question object.
      Set after_id to null to append, or specify an existing question id to
      insert after it.
    - update_question: Replace an existing question entirely. Provide the
      question_id of the question to replace and the new question object.
    - remove_question: Delete a question by id.
    - reorder_questions: Reorder all questions by providing the complete list
      of question ids in the desired order.

    Rules:
    - Use the minimal set of operations needed. For example, to change only
      the title, emit a single set_title.
    - When creating a brand new form, emit a set_title, set_description, and
      one add_question per question.
    - Each question has an id (q1, q2, q3, ...) that defines display order
      and must start from q1.
    - New questions must use ids that don't conflict with existing questions.
    - Questions can be one of three answer types:
      - "text": a free-text input. Only text and required apply.
      - "select": a single-choice dropdown. Must include options (list of
        2–6 choices); the respondent picks exactly one.
      - "checkbox": a multi-select checkbox group. Must include options
        (list of 2–6 choices); the respondent can pick multiple.
    - The required field indicates whether the question must be answered.
    - Question text must be clear, concise, and specific. Use second person
      ("you") where natural.
    - Do not include instructions like "select all that apply" in the question
      text — use the "checkbox" answer type instead.
    - Generate 3–10 questions unless the user specifies otherwise.
    - Title must be clear, concise, and reflect the form's purpose.
    - Description should explain the form's purpose and what data it collects.
    - If the user instruction changes the form's topic or scope, use
      set_title and set_description to update accordingly.
    - If the prompt is vague or outside form generation, make reasonable
      assumptions or return an empty instructions list.
    - Output ONLY valid JSON matching the schema. No explanations, no markdown.
"""


async def run_inference(
    client: AsyncGroq,
    conversation_history: List[ChatCompletionMessageParam],
) -> ChatCompletionMessage:
    completion = await client.chat.completions.create(
        model=GROQ_MODEL,
        messages=conversation_history,
        max_completion_tokens=1024,
        reasoning_format="hidden",
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "form_instructions",
                "description": "A list of editing operations for form modification",
                "schema": InstructionBatch.model_json_schema(),
            },
        },
    )

    return completion.choices[0].message


def parse_message(message: ChatCompletionMessage) -> Optional[InstructionBatch]:
    if message.content:
        raw_output = json.loads(message.content)
        validated_output = InstructionBatch.model_validate(raw_output)
        return validated_output
