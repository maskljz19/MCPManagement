"""Authentication Service"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis
from app.models.user import UserModel, UserRole
from app.models.api_key import APIKeyModel
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    extract_role_from_token,
    verify_api_key as verify_api_key_hash
)
from app.core.permissions import check_permission, get_permissions_for_role
from app.services.cache_service import CacheService


class AuthService:
    """
    Authentication and authorization service.
    
    Handles user authentication via password or API key,
    JWT token generation and validation, and RBAC permission checking.
    """
    
    def __init__(self, db_session: AsyncSession, cache: Optional[Redis] = None):
        """
        Initialize the authentication service.
        
        Args:
            db_session: Database session for user/API key queries
            cache: Redis client for session management (optional)
        """
        self.db = db_session
        self.cache = cache
        self.cache_service = CacheService(cache) if cache else None
    
    async def authenticate_user(
        self,
        username: str,
        password: str
    ) -> Optional[UserModel]:
        """
        Authenticate a user with username and password.
        
        Args:
            username: Username or email
            password: Plain text password
            
        Returns:
            UserModel if authentication successful, None otherwise
        """
        # Try to find user by username or email
        stmt = select(UserModel).where(
            (UserModel.username == username) | (UserModel.email == username)
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None:
            return None
        
        # Check if user is active
        if not user.is_active:
            return None
        
        # Verify password
        if not verify_password(password, user.password_hash):
            return None
        
        return user
    
    async def create_tokens(
        self,
        user: UserModel
    ) -> Tuple[str, str, int]:
        """
        Create access and refresh tokens for a user.
        
        Ensures role normalization for consistent JWT token claims.
        
        Args:
            user: User model instance
            
        Returns:
            Tuple of (access_token, refresh_token, expires_in_seconds)
            
        Raises:
            AuthenticationError: If role normalization fails
        """
        from app.core.exceptions import RoleValidationError, AuthenticationError
        from app.core.logging_config import get_logger
        
        logger = get_logger(__name__)
        
        try:
            # Ensure user role is properly normalized
            # This handles cases where user data might have been stored with different formats
            normalized_role = user.role
            if isinstance(user.role, str):
                normalized_role = UserRole.normalize(user.role)
            
            # Log role normalization if it occurred
            if str(user.role) != normalized_role.value:
                logger.info(
                    "token_creation_role_normalized",
                    user_id=str(user.id),
                    original_role=str(user.role),
                    normalized_role=normalized_role.value,
                    context="AuthService.create_tokens"
                )
            
        except RoleValidationError as e:
            # Log the error and provide graceful degradation
            logger.error(
                "token_creation_role_validation_failed",
                user_id=str(user.id),
                invalid_role=str(user.role),
                valid_roles=e.valid_roles,
                context="AuthService.create_tokens",
                error_details=e.details,
                exc_info=True
            )
            
            # For token creation, we can gracefully degrade to VIEWER role
            # This ensures users can still authenticate even with corrupted role data
            normalized_role = UserRole.VIEWER
            logger.warning(
                "token_creation_role_degraded",
                user_id=str(user.id),
                degraded_to=normalized_role.value,
                reason="role_validation_failed",
                context="AuthService.create_tokens"
            )
        
        # Get user permissions based on normalized role
        permissions = get_permissions_for_role(normalized_role)
        
        # Create access token with normalized role
        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            role=normalized_role,
            permissions=permissions
        )
        
        # Create refresh token
        refresh_token = create_refresh_token(user_id=user.id)
        
        # Store refresh token in cache if available
        if self.cache_service:
            # Hash the refresh token for storage
            token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
            await self.cache_service.store_refresh_token(
                token_hash=token_hash,
                user_id=UUID(user.id)
            )
        
        # Calculate expiry in seconds
        from app.core.config import settings
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        logger.info(
            "tokens_created_successfully",
            user_id=str(user.id),
            username=user.username,
            role=normalized_role.value,
            expires_in=expires_in,
            context="AuthService.create_tokens"
        )
        
        return access_token, refresh_token, expires_in
    
    async def verify_access_token(self, token: str) -> Optional[dict]:
        """
        Verify an access token and return its payload.
        
        Args:
            token: JWT access token
            
        Returns:
            Token payload if valid, None otherwise
        """
        return verify_token(token)
    
    async def verify_refresh_token(self, token: str) -> Optional[UUID]:
        """
        Verify a refresh token and return the user ID.
        
        Args:
            token: JWT refresh token
            
        Returns:
            User ID if valid, None otherwise
        """
        payload = verify_token(token)
        if payload is None:
            return None
        
        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            return None
        
        # Extract user ID
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        
        try:
            return UUID(user_id_str)
        except (ValueError, AttributeError):
            return None
    
    async def refresh_access_token(
        self,
        refresh_token: str
    ) -> Optional[Tuple[str, int]]:
        """
        Generate a new access token using a refresh token.
        
        Ensures role normalization for consistent JWT token claims.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Tuple of (new_access_token, expires_in_seconds) if successful, None otherwise
        """
        from app.core.exceptions import RoleValidationError, TokenValidationError
        from app.core.logging_config import get_logger
        
        logger = get_logger(__name__)
        
        # Verify refresh token and get user ID
        user_id = await self.verify_refresh_token(refresh_token)
        if user_id is None:
            logger.warning(
                "refresh_token_verification_failed",
                context="AuthService.refresh_access_token"
            )
            return None
        
        # Get user from database
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None or not user.is_active:
            logger.warning(
                "refresh_token_user_not_found_or_inactive",
                user_id=str(user_id),
                context="AuthService.refresh_access_token"
            )
            return None
        
        try:
            # Ensure user role is properly normalized
            # This handles cases where user data might have been updated with different formats
            normalized_role = user.role
            if isinstance(user.role, str):
                normalized_role = UserRole.normalize(user.role)
            
            # Log role normalization if it occurred
            if str(user.role) != normalized_role.value:
                logger.info(
                    "refresh_token_role_normalized",
                    user_id=str(user.id),
                    original_role=str(user.role),
                    normalized_role=normalized_role.value,
                    context="AuthService.refresh_access_token"
                )
            
        except RoleValidationError as e:
            # Log the error and provide graceful degradation
            logger.error(
                "refresh_token_role_validation_failed",
                user_id=str(user.id),
                invalid_role=str(user.role),
                valid_roles=e.valid_roles,
                context="AuthService.refresh_access_token",
                error_details=e.details,
                exc_info=True
            )
            
            # For token refresh, we can gracefully degrade to VIEWER role
            # This ensures users can still use their refresh tokens even with corrupted role data
            normalized_role = UserRole.VIEWER
            logger.warning(
                "refresh_token_role_degraded",
                user_id=str(user.id),
                degraded_to=normalized_role.value,
                reason="role_validation_failed",
                context="AuthService.refresh_access_token"
            )
        
        # Get user permissions based on normalized role
        permissions = get_permissions_for_role(normalized_role)
        
        # Create new access token with normalized role
        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            role=normalized_role,
            permissions=permissions
        )
        
        # Calculate expiry
        from app.core.config import settings
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        logger.info(
            "access_token_refreshed_successfully",
            user_id=str(user.id),
            username=user.username,
            role=normalized_role.value,
            expires_in=expires_in,
            context="AuthService.refresh_access_token"
        )
        
        return access_token, expires_in
    
    async def authenticate_api_key(self, api_key: str) -> Optional[UserModel]:
        """
        Authenticate a user using an API key.
        
        Args:
            api_key: Plain API key string
            
        Returns:
            UserModel if authentication successful, None otherwise
        """
        # Get all API keys (we need to check hashes)
        stmt = select(APIKeyModel).where(APIKeyModel.revoked_at.is_(None))
        result = await self.db.execute(stmt)
        api_keys = result.scalars().all()
        
        # Find matching API key
        matched_key = None
        for key in api_keys:
            if verify_api_key_hash(api_key, key.key_hash):
                matched_key = key
                break
        
        if matched_key is None:
            return None
        
        # Check if key is valid (not expired)
        if not matched_key.is_valid():
            return None
        
        # Update last used timestamp
        matched_key.last_used_at = datetime.utcnow()
        await self.db.commit()
        
        # Get associated user
        stmt = select(UserModel).where(UserModel.id == matched_key.user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None or not user.is_active:
            return None
        
        return user
    
    def check_permission(
        self,
        user: UserModel,
        resource: str,
        action: str
    ) -> bool:
        """
        Check if a user has permission to perform an action on a resource.
        
        Ensures role normalization for consistent permission checking.
        
        Args:
            user: User model instance
            resource: Resource name (e.g., "mcps", "knowledge")
            action: Action name (e.g., "create", "read", "update", "delete")
            
        Returns:
            True if user has permission, False otherwise
        """
        from app.core.exceptions import RoleValidationError
        from app.core.logging_config import get_logger
        
        logger = get_logger(__name__)
        
        try:
            # Ensure user role is properly normalized for permission checking
            normalized_role = user.role
            if isinstance(user.role, str):
                normalized_role = UserRole.normalize(user.role)
            
            return check_permission(normalized_role, resource, action)
            
        except RoleValidationError as e:
            # Log the error and deny permission for invalid roles
            logger.error(
                "permission_check_role_validation_failed",
                user_id=str(user.id),
                invalid_role=str(user.role),
                resource=resource,
                action=action,
                valid_roles=e.valid_roles,
                context="AuthService.check_permission",
                error_details=e.details,
                exc_info=True
            )
            
            # Invalid role, deny permission for security
            return False
    
    async def create_session(
        self,
        user: UserModel,
        session_id: str,
        metadata: Optional[dict] = None
    ) -> None:
        """
        Create a user session in Redis.
        
        Ensures role normalization for consistent session data.
        
        Args:
            user: User model instance
            session_id: Unique session identifier
            metadata: Additional session metadata (e.g., IP, user agent)
        """
        from app.core.exceptions import RoleValidationError
        from app.core.logging_config import get_logger
        
        if not self.cache_service:
            return
        
        logger = get_logger(__name__)
        
        try:
            # Ensure user role is properly normalized for session storage
            normalized_role = user.role
            if isinstance(user.role, str):
                normalized_role = UserRole.normalize(user.role)
            
        except RoleValidationError as e:
            # Log the error and use default role for session
            logger.error(
                "session_creation_role_validation_failed",
                user_id=str(user.id),
                session_id=session_id,
                invalid_role=str(user.role),
                valid_roles=e.valid_roles,
                context="AuthService.create_session",
                error_details=e.details,
                exc_info=True
            )
            
            # Use default role if normalization fails
            normalized_role = UserRole.VIEWER
            logger.warning(
                "session_creation_role_degraded",
                user_id=str(user.id),
                session_id=session_id,
                degraded_to=normalized_role.value,
                reason="role_validation_failed",
                context="AuthService.create_session"
            )
        
        session_data = {
            "user_id": str(user.id),
            "username": user.username,
            "role": normalized_role.value,  # Always store as lowercase string
            "metadata": metadata or {}
        }
        
        await self.cache_service.create_session(session_id, session_data)
        
        logger.info(
            "session_created_successfully",
            user_id=str(user.id),
            session_id=session_id,
            role=normalized_role.value,
            context="AuthService.create_session"
        )
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """
        Retrieve a user session from Redis.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data if exists, None otherwise
        """
        if not self.cache_service:
            return None
        
        return await self.cache_service.get_session(session_id)
    
    async def delete_session(self, session_id: str) -> None:
        """
        Delete a user session from Redis.
        
        Args:
            session_id: Session identifier
        """
        if not self.cache_service:
            return
        
        await self.cache_service.delete_session(session_id)
    
    async def revoke_refresh_token(self, refresh_token: str) -> None:
        """
        Revoke a refresh token (logout).
        
        Args:
            refresh_token: Refresh token to revoke
        """
        if not self.cache_service:
            return
        
        # Hash the refresh token
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        
        # Delete from cache
        await self.cache_service.delete_refresh_token(token_hash)
    
    async def validate_and_normalize_user_role(self, user: UserModel) -> UserModel:
        """
        Validate and normalize a user's role for backward compatibility.
        
        This method ensures that users with roles stored in different formats
        (e.g., from before the enum fix) are handled correctly.
        
        Args:
            user: User model instance
            
        Returns:
            User model with normalized role
        """
        from app.core.exceptions import RoleValidationError, BackwardCompatibilityError
        from app.core.logging_config import get_logger
        
        logger = get_logger(__name__)
        
        try:
            # If role is already a UserRole enum, ensure it's valid
            if isinstance(user.role, UserRole):
                return user
            
            # If role is a string, normalize it
            if isinstance(user.role, str):
                original_role = user.role
                normalized_role = UserRole.normalize(user.role)
                user.role = normalized_role
                
                # Log if normalization changed the value (backward compatibility)
                if original_role != normalized_role.value:
                    logger.info(
                        "user_role_normalized_during_validation",
                        user_id=str(user.id),
                        original_role=original_role,
                        normalized_role=normalized_role.value,
                        context="AuthService.validate_and_normalize_user_role"
                    )
                
                # Update in database for consistency
                await self.db.commit()
                return user
            
            # If role is None or invalid type, set default
            logger.warning(
                "user_role_set_to_default",
                user_id=str(user.id),
                original_role=str(user.role),
                original_type=type(user.role).__name__,
                default_role=UserRole.VIEWER.value,
                context="AuthService.validate_and_normalize_user_role"
            )
            
            user.role = UserRole.VIEWER
            await self.db.commit()
            return user
            
        except RoleValidationError as e:
            # Log backward compatibility issue
            compatibility_error = BackwardCompatibilityError(
                message=f"Invalid role '{user.role}' for user {user.id}, setting to VIEWER",
                compatibility_issue="invalid_role_data",
                user_id=str(user.id),
                details={
                    "original_role": str(user.role),
                    "valid_roles": e.valid_roles,
                    "error_context": e.context
                }
            )
            
            logger.error(
                "backward_compatibility_role_issue",
                **compatibility_error.to_dict(),
                context="AuthService.validate_and_normalize_user_role",
                exc_info=True
            )
            
            # Set to default role for backward compatibility
            user.role = UserRole.VIEWER
            await self.db.commit()
            return user
    
    async def authenticate_with_role_validation(
        self,
        username: str,
        password: str
    ) -> Optional[UserModel]:
        """
        Authenticate a user with role validation and normalization.
        
        This method combines authentication with role normalization
        to ensure backward compatibility.
        
        Args:
            username: Username or email
            password: Plain text password
            
        Returns:
            UserModel with normalized role if authentication successful, None otherwise
        """
        from app.core.logging_config import get_logger
        
        logger = get_logger(__name__)
        
        # First authenticate normally
        user = await self.authenticate_user(username, password)
        if user is None:
            logger.info(
                "authentication_failed",
                username=username,
                context="AuthService.authenticate_with_role_validation"
            )
            return None
        
        # Validate and normalize the user's role
        try:
            normalized_user = await self.validate_and_normalize_user_role(user)
            
            logger.info(
                "authentication_successful_with_role_validation",
                user_id=str(normalized_user.id),
                username=normalized_user.username,
                role=normalized_user.role.value,
                context="AuthService.authenticate_with_role_validation"
            )
            
            return normalized_user
            
        except Exception as e:
            # Log the error but don't fail authentication
            logger.error(
                "role_validation_failed_during_authentication",
                user_id=str(user.id),
                username=user.username,
                error_message=str(e),
                context="AuthService.authenticate_with_role_validation",
                exc_info=True
            )
            
            # Return user with potentially unnormalized role
            # The calling code should handle this gracefully
            return user
