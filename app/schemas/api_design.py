"""System Design Interview Simulator - API Design Schemas.

Defines Pydantic schemas for candidate API contract proposals, REST/gRPC/WebSocket
endpoint definitions, request/response parameters, status codes, and rate limiting specifications.
"""

from enum import StrEnum
from typing import Any
import uuid
from pydantic import Field

from app.schemas import BaseSchema


class HttpMethodEnum(StrEnum):
    """Standard HTTP request verbs supported in API designs."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ParameterLocationEnum(StrEnum):
    """Network request location where a parameter is transmitted."""

    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    BODY = "body"
    COOKIE = "cookie"


class ProtocolTypeEnum(StrEnum):
    """Communication paradigm and interface specification protocol."""

    REST = "REST"
    GRPC = "gRPC"
    GRAPHQL = "GraphQL"
    WEBSOCKET = "WebSocket"
    ASYNC_RPC = "AsyncRPC"


class AuthTypeEnum(StrEnum):
    """Authentication and authorization mechanism for endpoint protection."""

    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    OAUTH2 = "oauth2"
    MTLS = "mtls"


class ParameterSchema(BaseSchema):
    """Individual query, path, header, or body parameter in an API contract."""

    name: str = Field(
        ...,
        description="Name of the parameter identifier.",
        examples=["short_code", "limit", "Authorization"],
    )
    location: ParameterLocationEnum = Field(
        ...,
        description="Where the parameter is conveyed in the HTTP request.",
        examples=[ParameterLocationEnum.PATH],
    )
    data_type: str = Field(
        default="string",
        description="Data type (string, integer, float, boolean, uuid, object, array).",
        examples=["string"],
    )
    required: bool = Field(
        default=True,
        description="Whether this parameter is mandatory for the operation.",
    )
    description: str | None = Field(
        default=None,
        description="Functional explanation of the parameter purpose.",
        examples=["Seven-character alphanumeric shortened slug identifier."],
    )
    default_value: Any = Field(
        default=None,
        description="Default value applied when parameter is omitted.",
    )
    example: Any = Field(
        default=None,
        description="Representative sample parameter value.",
        examples=["aB9zQ1x"],
    )


class ApiResponseDesignSchema(BaseSchema):
    """Expected response status, headers, and structure returned by an endpoint."""

    status_code: int = Field(
        ...,
        ge=100,
        le=599,
        description="Standard HTTP status code (e.g. 200, 201, 301, 400, 429).",
        examples=[301],
    )
    description: str = Field(
        ...,
        description="Description of what this response status indicates.",
        examples=["Permanent redirect to original destination URL."],
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Key-value pairs of required response headers.",
        examples=[{"Location": "https://example.com/target-page"}],
    )
    schema_definition: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON schema or payload structure definition.",
    )
    example_body: Any = Field(
        default=None,
        description="Representative sample response payload.",
    )


class RateLimitDesignSchema(BaseSchema):
    """Rate limiting and throttling policy applied to the endpoint."""

    enabled: bool = Field(
        default=True,
        description="Whether rate limiting is enforced on this endpoint.",
    )
    requests_per_window: int = Field(
        default=100,
        ge=1,
        description="Maximum allowed requests within the time window.",
        examples=[1000],
    )
    window_seconds: int = Field(
        default=60,
        ge=1,
        description="Duration of the throttling window in seconds.",
        examples=[60],
    )
    strategy: str = Field(
        default="Token Bucket per User / IP",
        description="Throttling algorithm and partitioning key.",
        examples=["Distributed Redis Token Bucket partitioned by client_id"],
    )


class EndpointDesignSchema(BaseSchema):
    """Complete specification of an individual API endpoint proposed by candidate."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())[:8],
        description="Unique identifier for the endpoint design.",
        examples=["ep-redirect-url"],
    )
    path: str = Field(
        ...,
        description="URI resource path template with optional route parameters.",
        examples=["/api/v1/urls/{short_code}"],
    )
    method: HttpMethodEnum = Field(
        default=HttpMethodEnum.GET,
        description="HTTP request verb.",
        examples=[HttpMethodEnum.GET],
    )
    protocol: ProtocolTypeEnum = Field(
        default=ProtocolTypeEnum.REST,
        description="Communication protocol paradigm.",
        examples=[ProtocolTypeEnum.REST],
    )
    summary: str = Field(
        ...,
        description="Brief summary of endpoint responsibility.",
        examples=["Resolve shortened URL and issue 301 redirect."],
    )
    description: str | None = Field(
        default=None,
        description="Detailed behavior, caching semantics, and side effects.",
    )
    auth_type: AuthTypeEnum = Field(
        default=AuthTypeEnum.NONE,
        description="Authentication paradigm required for invocation.",
        examples=[AuthTypeEnum.NONE],
    )
    parameters: list[ParameterSchema] = Field(
        default_factory=list,
        description="List of path, query, and header parameters accepted.",
    )
    request_body_schema: dict[str, Any] | None = Field(
        default=None,
        description="Structure of the request payload for POST/PUT/PATCH methods.",
    )
    responses: list[ApiResponseDesignSchema] = Field(
        default_factory=list,
        description="List of standard responses and error codes returned.",
    )
    rate_limiting: RateLimitDesignSchema | None = Field(
        default=None,
        description="Rate limiting constraints specified for this endpoint.",
    )
    is_idempotent: bool = Field(
        default=True,
        description="Whether the endpoint guarantees idempotency.",
    )
    target_service: str | None = Field(
        default=None,
        description="Backend service or microservice handling this request.",
        examples=["URL Redirection Service"],
    )


class ApiDesignSubmissionSchema(BaseSchema):
    """Aggregated API design contract submitted during architecture review."""

    session_id: uuid.UUID = Field(
        ...,
        description="Associated interview session UUID.",
    )
    protocol: ProtocolTypeEnum = Field(
        default=ProtocolTypeEnum.REST,
        description="Primary protocol chosen for the public API.",
    )
    endpoints: list[EndpointDesignSchema] = Field(
        default_factory=list,
        description="Complete set of candidate endpoints.",
    )
    global_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Global headers applied across all endpoints (e.g. idempotency keys, tracing).",
    )
    notes: str | None = Field(
        default=None,
        description="Candidate notes on API evolution, versioning, or backward compatibility.",
    )
