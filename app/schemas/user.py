"""System Design Interview Simulator - User Schemas and DTOs.

Defines Pydantic schemas for candidate registration, profile queries, updates,
and authentication token responses.
"""

import uuid
from datetime import datetime
from pydantic import Field, field_validator

from app.core.constants import SeniorityLevel
from app.schemas import BaseSchema


class UserBase(BaseSchema):
    """Base user attributes shared across input and output representations."""

    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Unique user email address.",
        examples=["candidate@example.com"],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Full candidate or interviewer name.",
        examples=["Jane Doe"],
    )
    seniority_level: SeniorityLevel = Field(
        default=SeniorityLevel.SENIOR,
        description="Target engineering seniority level for interview calibration.",
        examples=[SeniorityLevel.SENIOR],
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Strip whitespace and lowercase email address."""
        if isinstance(v, str):
            v = v.strip().lower()
            if "@" not in v or "." not in v.split("@")[-1]:
                raise ValueError("Invalid email format.")
        return v


class UserCreate(UserBase):
    """Schema for candidate registration and account creation."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Plaintext password (hashed before persistence with PBKDF2).",
        examples=["SecurePassw0rd!"],
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Ensure password meets minimum complexity constraints."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return v


class UserUpdate(BaseSchema):
    """Schema for updating candidate profile information."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated full name.",
    )
    seniority_level: SeniorityLevel | None = Field(
        default=None,
        description="Updated seniority level.",
    )
    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="Updated plaintext password.",
    )
    is_active: bool | None = Field(
        default=None,
        description="Account active status flag.",
    )


class UserRead(UserBase):
    """Schema for returning user account details."""

    id: uuid.UUID = Field(description="Unique user identifier.")
    is_active: bool = Field(description="Indicates whether user account is active.")
    is_admin: bool = Field(description="Indicates whether user holds administrative privileges.")
    created_at: datetime = Field(description="Account creation UTC timestamp.")
    updated_at: datetime = Field(description="Last profile modification UTC timestamp.")


class UserSummary(BaseSchema):
    """Compact user profile schema for nested session or message payloads."""

    id: uuid.UUID = Field(description="Unique user identifier.")
    name: str = Field(description="Full candidate name.")
    email: str = Field(description="User email address.")
    seniority_level: SeniorityLevel = Field(description="Target engineering level.")


class UserLogin(BaseSchema):
    """Payload for candidate authentication credentials."""

    email: str = Field(..., description="Registered user email.")
    password: str = Field(..., description="Account password.")


class UserTokenResponse(BaseSchema):
    """Authentication token payload returned upon successful login."""

    access_token: str = Field(description="Cryptographically signed session or access token.")
    token_type: str = Field(default="bearer", description="Token schema type.")
    user: UserRead = Field(description="Authenticated user profile details.")
