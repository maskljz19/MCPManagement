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
        
        Args:
            user: User model instance
            
        Returns:
            Tuple of (access_token, refresh_token, expires_in_seconds)
        """
        # Get user permissions based on role
        permissions = get_permissions_for_role(user.role)
        
        # Create access token
        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
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
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Tuple of (new_access_token, expires_in_seconds) if successful, None otherwise
        """
        # Verify refresh token and get user ID
        user_id = await self.verify_refresh_token(refresh_token)
        if user_id is None:
            return None
        
        # Get user from database
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None or not user.is_active:
            return None
        
        # Get user permissions
        permissions = get_permissions_for_role(user.role)
        
        # Create new access token
        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            permissions=permissions
        )
        
        # Calculate expiry
        from app.core.config import settings
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
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
        
        Args:
            user: User model instance
            resource: Resource name (e.g., "mcps", "knowledge")
            action: Action name (e.g., "create", "read", "update", "delete")
            
        Returns:
            True if user has permission, False otherwise
        """
        return check_permission(user.role, resource, action)
    
    async def create_session(
        self,
        user: UserModel,
        session_id: str,
        metadata: Optional[dict] = None
    ) -> None:
        """
        Create a user session in Redis.
        
        Args:
            user: User model instance
            session_id: Unique session identifier
            metadata: Additional session metadata (e.g., IP, user agent)
        """
        if not self.cache_service:
            return
        
        session_data = {
            "user_id": str(user.id),
            "username": user.username,
            "role": user.role.value,
            "metadata": metadata or {}
        }
        
        await self.cache_service.create_session(session_id, session_data)
    
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
