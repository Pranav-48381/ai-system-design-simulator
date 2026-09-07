"""System Design Interview Simulator - Domain Exceptions.

Provides a unified hierarchy of application exceptions with HTTP status codes,
machine-readable error codes, and contextual detail payloads.
"""

from typing import Any


class AppException(Exception):
    """Base application exception for all domain-specific errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize exception to structured RFC-7807 compatible error payload."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
        }


class EntityNotFoundError(AppException):
    """Raised when a requested database entity or resource is not found."""

    def __init__(
        self,
        entity_name: str,
        entity_id: Any,
        details: dict[str, Any] | None = None,
    ) -> None:
        message = f"{entity_name} with identifier '{entity_id}' was not found."
        super().__init__(
            message=message,
            error_code=f"{entity_name.upper()}_NOT_FOUND",
            status_code=404,
            details=details,
        )


class EntityAlreadyExistsError(AppException):
    """Raised when attempting to create a resource that already exists."""

    def __init__(
        self,
        entity_name: str,
        identifier: Any,
        details: dict[str, Any] | None = None,
    ) -> None:
        message = f"{entity_name} with identifier '{identifier}' already exists."
        super().__init__(
            message=message,
            error_code=f"{entity_name.upper()}_ALREADY_EXISTS",
            status_code=409,
            details=details,
        )


class ValidationError(AppException):
    """Raised when input validation fails outside Pydantic validation."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class InvalidStateTransitionError(AppException):
    """Raised when attempting an illegal transition in the interview state machine."""

    def __init__(
        self,
        current_state: str,
        target_state: str,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        message = (
            f"Cannot transition from stage '{current_state}' to '{target_state}'."
            + (f" Reason: {reason}" if reason else "")
        )
        super().__init__(
            message=message,
            error_code="INVALID_STATE_TRANSITION",
            status_code=400,
            details=details,
        )


class SessionTerminatedError(AppException):
    """Raised when actions are attempted on an already terminated interview session."""

    def __init__(
        self,
        session_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=f"Interview session '{session_id}' is closed or terminated.",
            error_code="SESSION_TERMINATED",
            status_code=400,
            details=details,
        )


class StageLimitExceededError(AppException):
    """Raised when turn or time limits for an interview stage are exceeded."""

    def __init__(
        self,
        stage: str,
        limit_type: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=f"Limit exceeded for stage '{stage}': {limit_type}.",
            error_code="STAGE_LIMIT_EXCEEDED",
            status_code=400,
            details=details,
        )


class AuthenticationError(AppException):
    """Raised when user or WebSocket authentication fails."""

    def __init__(
        self,
        message: str = "Invalid or expired authentication credentials.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_FAILED",
            status_code=401,
            details=details,
        )


class AuthorizationError(AppException):
    """Raised when user lacks permission to access the specified resource."""

    def __init__(
        self,
        message: str = "Insufficient permissions to perform this operation.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_FAILED",
            status_code=403,
            details=details,
        )


class WebSocketProtocolError(AppException):
    """Raised when an incoming WebSocket frame violates the protocol contract."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="WS_PROTOCOL_ERROR",
            status_code=400,
            details=details,
        )


class RateLimitExceededError(AppException):
    """Raised when client exceeds allowed message or API invocation rates."""

    def __init__(
        self,
        retry_after_seconds: int = 60,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=f"Rate limit exceeded. Please retry after {retry_after_seconds}s.",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after_seconds": retry_after_seconds, **(details or {})},
        )


class LLMProviderError(AppException):
    """Raised when an external LLM provider API returns an error or failure."""

    def __init__(
        self,
        provider: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=f"LLM provider '{provider}' error: {message}",
            error_code="LLM_PROVIDER_ERROR",
            status_code=502,
            details={"provider": provider, **(details or {})},
        )


class LLMTimeoutError(AppException):
    """Raised when an LLM inference call times out."""

    def __init__(
        self,
        provider: str,
        timeout_seconds: float,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=f"LLM request to provider '{provider}' timed out after {timeout_seconds}s.",
            error_code="LLM_TIMEOUT",
            status_code=504,
            details={"provider": provider, "timeout_seconds": timeout_seconds, **(details or {})},
        )


class LLMResponseParsingError(AppException):
    """Raised when LLM output cannot be parsed into the expected structured format."""

    def __init__(
        self,
        expected_schema: str,
        raw_content: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=f"Failed to parse LLM response into schema '{expected_schema}'.",
            error_code="LLM_PARSING_FAILED",
            status_code=500,
            details={"expected_schema": expected_schema, "raw_snippet": raw_content[:200], **(details or {})},
        )


class DatabaseConnectionError(AppException):
    """Raised when connecting to PostgreSQL fails."""

    def __init__(
        self,
        message: str = "Unable to connect to relational database.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="DATABASE_CONNECTION_ERROR",
            status_code=503,
            details=details,
        )


class DatabaseTransactionError(AppException):
    """Raised when an async database transaction fails or encounters a conflict."""

    def __init__(
        self,
        message: str = "Database transaction failed and was rolled back.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="DATABASE_TRANSACTION_ERROR",
            status_code=500,
            details=details,
        )
