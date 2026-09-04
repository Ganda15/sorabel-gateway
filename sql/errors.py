from __future__ import annotations

from enum import Enum


class SqlErrorCode(str, Enum):
    AMBIGUOUS_QUESTION = "AMBIGUOUS_QUESTION"
    OUT_OF_SCHEMA = "OUT_OF_SCHEMA"
    UNSUPPORTED_QUESTION = "UNSUPPORTED_QUESTION"
    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    UNSAFE_SQL = "UNSAFE_SQL"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    NOT_FOUND = "NOT_FOUND"
    QUERY_LIMIT_EXCEEDED = "QUERY_LIMIT_EXCEEDED"
    EXECUTION_ERROR = "EXECUTION_ERROR"


_STATUS_BY_CODE = {
    SqlErrorCode.AMBIGUOUS_QUESTION: "clarification",
    SqlErrorCode.OUT_OF_SCHEMA: "refused",
    SqlErrorCode.UNSUPPORTED_QUESTION: "refused",
    SqlErrorCode.NOT_AUTHORIZED: "refused",
    SqlErrorCode.UNSAFE_SQL: "refused",
    SqlErrorCode.INVALID_ARGUMENT: "refused",
    SqlErrorCode.NOT_FOUND: "refused",
    SqlErrorCode.QUERY_LIMIT_EXCEEDED: "refused",
    SqlErrorCode.EXECUTION_ERROR: "execution_error",
}


class SqlServiceError(Exception):
    def __init__(self, code: SqlErrorCode, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message
        self.status = _STATUS_BY_CODE[code]
