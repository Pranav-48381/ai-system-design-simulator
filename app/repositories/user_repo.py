"""System Design Interview Simulator - User Repository.

Provides specialized asynchronous data access operations for candidate and administrator
user accounts, including email lookups, password hashing authentication, and seniority updates.
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SeniorityLevel
from app.core.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from app.core.logging import get_logger
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class UserRepository(BaseRepository[User]):
    """Repository handling persistence, authentication, and lifecycle for User accounts."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize UserRepository with active AsyncSession."""
        super().__init__(User, session)

    async def get_by_email(self, email: str, include_deleted: bool = False) -> User | None:
        """Query a user by normalized email address.

        Args:
            email: User's login email address.
            include_deleted: Whether to include soft-deleted accounts.

        Returns:
            The User instance if found, or None.
        """
        normalized_email = email.strip().lower()
        stmt = select(User).where(func.lower(User.email) == normalized_email)
        if not include_deleted:
            stmt = stmt.where(User.is_deleted.is_(False))

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_or_raise(self, email: str, include_deleted: bool = False) -> User:
        """Query a user by email or raise EntityNotFoundError if not found.

        Args:
            email: User's login email address.
            include_deleted: Whether to include soft-deleted accounts.

        Returns:
            The persisted User instance.

        Raises:
            EntityNotFoundError: If no matching account is found.
        """
        user = await self.get_by_email(email, include_deleted=include_deleted)
        if user is None:
            raise EntityNotFoundError(entity_name="User", entity_id=email)
        return user

    async def email_exists(self, email: str, exclude_user_id: uuid.UUID | None = None) -> bool:
        """Check whether an email address is already registered.

        Args:
            email: Email address to verify.
            exclude_user_id: Optional user UUID to exclude (useful during profile updates).

        Returns:
            True if email already exists in the system, False otherwise.
        """
        normalized_email = email.strip().lower()
        stmt = select(func.count()).select_from(User).where(
            func.lower(User.email) == normalized_email,
            User.is_deleted.is_(False),
        )
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)

        result = await self._session.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def create_user(
        self,
        email: str,
        name: str,
        password: str,
        seniority_level: SeniorityLevel = SeniorityLevel.SENIOR,
        is_admin: bool = False,
    ) -> User:
        """Create and persist a new user account with hashed password.

        Args:
            email: User login email.
            name: Full display name.
            password: Plaintext password to be hashed securely.
            seniority_level: Target technical seniority tier.
            is_admin: Whether account has administrator privileges.

        Returns:
            The created and persisted User instance.

        Raises:
            EntityAlreadyExistsError: If email is already in use.
        """
        normalized_email = email.strip().lower()
        if await self.email_exists(normalized_email):
            logger.warning("Attempted registration with existing email: %s", normalized_email)
            raise EntityAlreadyExistsError(entity_name="User", identifier=normalized_email)

        user = User(
            email=normalized_email,
            name=name.strip(),
            hashed_password=hash_password(password),
            seniority_level=seniority_level,
            is_active=True,
            is_admin=is_admin,
        )
        return await self.create(user, flush=True)

    async def authenticate(self, email: str, password: str) -> User | None:
        """Authenticate user credentials using PBKDF2 password verification.

        Args:
            email: User's login email.
            password: Provided plaintext password.

        Returns:
            The authenticated User instance if credentials are valid, None otherwise.
        """
        user = await self.get_by_email(email, include_deleted=False)
        if user is None:
            logger.info("Authentication failed: account '%s' not found", email)
            return None

        if not user.is_active or user.is_deleted:
            logger.warning("Authentication failed: account '%s' is inactive or deleted", email)
            return None

        if not verify_password(password, user.hashed_password):
            logger.info("Authentication failed: invalid password for '%s'", email)
            return None

        logger.info("User '%s' authenticated successfully", email)
        return user

    async def update_password(self, user_id: uuid.UUID, new_password: str) -> User:
        """Update and rehash password for an existing user account.

        Args:
            user_id: User UUID.
            new_password: New plaintext password.

        Returns:
            The updated User instance.
        """
        user = await self.get_or_raise(user_id)
        user.hashed_password = hash_password(new_password)
        await self._session.flush()
        await self._session.refresh(user)
        logger.info("Password successfully updated for user %s", user_id)
        return user

    async def update_profile(
        self,
        user_id: uuid.UUID,
        name: str | None = None,
        seniority_level: SeniorityLevel | None = None,
        is_active: bool | None = None,
    ) -> User:
        """Update profile attributes of an existing user account.

        Args:
            user_id: User UUID.
            name: Optional updated full name.
            seniority_level: Optional updated seniority tier.
            is_active: Optional updated active status flag.

        Returns:
            The updated User instance.
        """
        user = await self.get_or_raise(user_id)
        if name is not None:
            user.name = name.strip()
        if seniority_level is not None:
            user.seniority_level = seniority_level
        if is_active is not None:
            user.is_active = is_active

        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def soft_delete(self, user_id: uuid.UUID) -> bool:
        """Soft delete a user account by marking is_deleted=True.

        Args:
            user_id: User UUID.

        Returns:
            True if account was soft-deleted, False if account not found.
        """
        user = await self.get_by_id(user_id)
        if user is None or user.is_deleted:
            return False

        user.is_deleted = True
        user.deleted_at = datetime.now(timezone.utc)
        user.is_active = False
        await self._session.flush()
        logger.info("User %s soft-deleted successfully", user_id)
        return True

    async def restore(self, user_id: uuid.UUID) -> bool:
        """Restore a previously soft-deleted user account.

        Args:
            user_id: User UUID.

        Returns:
            True if account was restored, False if not found or not deleted.
        """
        stmt = select(User).where(User.id == user_id, User.is_deleted.is_(True))
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return False

        user.is_deleted = False
        user.deleted_at = None
        user.is_active = True
        await self._session.flush()
        logger.info("User %s restored successfully", user_id)
        return True

    async def list_active(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Any = None,
    ) -> Sequence[User]:
        """Query active, non-deleted user accounts.

        Args:
            skip: Number of records to skip.
            limit: Maximum records to return.
            order_by: Optional order expression.

        Returns:
            Sequence of active User records.
        """
        filters = [User.is_deleted.is_(False), User.is_active.is_(True)]
        return await self.list_all(skip=skip, limit=limit, filters=filters, order_by=order_by)
