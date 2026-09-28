"""The one shape every failed request comes back in.

A single schema means the frontend has one thing to read: ``code`` to decide what to
do, ``message`` to show, and ``fields`` when a form can point at the offending input.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ErrorCode = Literal[
    # The thing asked for does not exist.
    "not_found",
    # The request was understood but the input is wrong; ``fields`` may say where.
    "invalid_input",
    # Anything unexpected on our side.
    "server_error",
]


class FieldErrorOut(BaseModel):
    """One input a form can mark, in the name the form used for it."""

    field: str
    message: str


class ErrorOut(BaseModel):
    code: ErrorCode
    # Written for the person reading the screen, not for a log.
    message: str
    fields: list[FieldErrorOut] = []
