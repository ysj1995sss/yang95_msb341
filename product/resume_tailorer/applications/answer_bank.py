"""Answers to custom application questions come only from answers the user
wrote and approved. Nothing is drafted or guessed: work authorization,
sponsorship, salary and similar questions are legal or personal statements."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from typing import Dict, List, Tuple

from resume_tailorer.applications.models import FormField


def question_text(field: FormField) -> str:
    return field.label or field.field_name


def question_key(question: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", question.lower()))


def apply_answer_bank(
    fields: List[FormField], answers: Dict[str, str]
) -> Tuple[List[FormField], Dict[str, str], List[str]]:
    """Fill still-empty questions from approved answers.

    Returns (fields, custom_answers {question: answer}, unanswered questions).
    File uploads are not questions and are skipped.
    """
    filled: List[FormField] = []
    custom: Dict[str, str] = {}
    unanswered: List[str] = []
    for field in fields:
        if field.prefilled or field.field_type == "file":
            filled.append(field)
            continue
        question = question_text(field)
        answer = answers.get(question_key(question))
        if answer:
            filled.append(replace(field, value=answer, prefilled=True))
            custom[question] = answer
        else:
            filled.append(field)
            if question_key(question) not in {question_key(q) for q in unanswered}:
                unanswered.append(question)
    return filled, custom, unanswered


def answers_version(custom_answers: Dict[str, str]) -> str:
    if not custom_answers:
        return ""
    return hashlib.sha256(json.dumps(custom_answers, sort_keys=True).encode("utf-8")).hexdigest()
