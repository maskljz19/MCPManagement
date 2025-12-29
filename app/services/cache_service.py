"""Cache Service - Redis caching utilities for MCP Platform"""

import json
import hashlib
from typing import Optional, Any, Dict, List
from uuid import UUID
from datetime import datetime, timedelta
from redis.asyncio import Redis


class CacheService:
    """
    Cache Service provides Redis caching utilities.
    
    Responsibilities:
    - Generate cache keys
    - Get/set/delete cache entries
    - Cache invalidation
    - Session management with TTL
    """
    
    # Cache TTL configurations (in seconds)
    TOOL_CACHE_TTL = 3600  # 1 hour
    LIST_CACHE_TTL = 300  # 5 minutes
    SESSION_TTL = 604800  # 7 days
    
    def __init__(self, redis: Redis):
        self.redis = redis
    
    # ========================================================================
    # Cache Key Generation
    # ========================================================================
    
    @staticmethod
    def generate_tool_key(tool_id: UUID) -> str:
        """Generate cache key for a single MCP tool"""
        return f"cache:mcp_tool:{tool_id}"
    
    @staticmethod
    def generate_list_key(filters: Dict[str, Any], pagination: Dict[str, Any]) -> str:
        """
        Generate cache key for tool list queries.
        
        Uses hash of filters and pagination to create unique key.
        """
        # Create a deterministic string from filters and pagination
        key_data = {
            "filters": filters,
            "pagination": pagination
        }
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"cache:mcp_tools:list:{key_hash}"
    
    @staticmethod
    def generate_session_key(session_id: str) -> str:
        """Generate cache key for user session"""
        return f"session:{session_id}"
    
    @staticmethod
    def generate_refresh_token_key(token_hash: str) -> str:
        """Generate cache key for refresh token"""
        return f"refresh_token:{token_hash}"
    
    # ========================================================================
    # Cache Operations - MCP Tools
    # ========================================================================
    
    async def get_tool(self, tool_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get cached MCP tool by ID.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            Tool data as dict if cached, None otherwise
        """
        key = self.generate_tool_key(tool_id)
        cached_data = await self.redis.get(key)
        
        if cached_data:
            return json.loads(cached_data)
        
        return None
    
    async def set_tool(
        self,
        tool_id: UUID,
        tool_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> None:
        """
        Cache an MCP tool.
        
        Args:
            tool_id: Tool identifier
            tool_data: Tool data to cache
            ttl: Time to live in seconds (default: TOOL_CACHE_TTL)
        """
        key = self.generate_tool_key(tool_id)
        ttl = ttl or self.TOOL_CACHE_TTL
        
        # Serialize tool data
        tool_json = json.dumps(tool_data, default=str)
        
        # Set with expiration
        await self.redis.setex(key, ttl, tool_json)
    
    async def delete_tool(self, tool_id: UUID) -> None:
        """
        Delete cached MCP tool.
        
        Args:
            tool_id: Tool identifier
        """
        key = self.generate_tool_key(tool_id)
        await self.redis.delete(key)
    
    async def get_tool_list(
        self,
        filters: Dict[str, Any],
        pagination: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached tool list results.
        
        Args:
            filters: Filter criteria
            pagination: Pagination parameters
            
        Returns:
            Cached list results if available, None otherwise
        """
        key = self.generate_list_key(filters, pagination)
        cached_data = await self.redis.get(key)
        
        if cached_data:
            return json.loads(cached_data)
        
        return None
    
    async def set_tool_list(
        self,
        filters: Dict[str, Any],
        pagination: Dict[str, Any],
        list_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> None:
        """
        Cache tool list results.
        
        Args:
            filters: Filter criteria
            pagination: Pagination parameters
            list_data: List results to cache
            ttl: Time to live in seconds (default: LIST_CACHE_TTL)
        """
        key = self.generate_list_key(filters, pagination)
        ttl = ttl or self.LIST_CACHE_TTL
        
        # Serialize list data
        list_json = json.dumps(list_data, default=str)
        
        # Set with expiration
        await self.redis.setex(key, ttl, list_json)
    
    async def invalidate_tool_lists(self) -> None:
        """
        Invalidate all cached tool lists.
        
        Called when any tool is created, updated, or deleted.
        """
        # Find all list cache keys
        pattern = "cache:mcp_tools:list:*"
        cursor = 0
        
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            
            if keys:
                await self.redis.delete(*keys)
            
            if cursor == 0:
                break
    
    # ========================================================================
    # Session Management
    # ========================================================================
    
    async def create_session(
        self,
        session_id: str,
        session_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> None:
        """
        Create a user session with TTL.
        
        Args:
            session_id: Unique session identifier
            session_data: Session data to store
            ttl: Time to live in seconds (default: SESSION_TTL)
        """
        key = self.generate_session_key(session_id)
        ttl = ttl or self.SESSION_TTL
        
        # Add metadata
        session_data["created_at"] = datetime.utcnow().isoformat()
        session_data["expires_at"] = (
            datetime.utcnow() + timedelta(seconds=ttl)
        ).isoformat()
        
        # Serialize session data
        session_json = json.dumps(session_data, default=str)
        
        # Set with expiration
        await self.redis.setex(key, ttl, session_json)
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a user session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data if exists and not expired, None otherwise
        """
        key = self.generate_session_key(session_id)
        cached_data = await self.redis.get(key)
        
        if cached_data:
            return json.loads(cached_data)
        
        return None
    
    async def delete_session(self, session_id: str) -> None:
        """
        Delete a user session.
        
        Args:
            session_id: Session identifier
        """
        key = self.generate_session_key(session_id)
        await self.redis.delete(key)
    
    async def refresh_session(
        self,
        session_id: str,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Refresh session TTL (extend expiration).
        
        Args:
            session_id: Session identifier
            ttl: New time to live in seconds (default: SESSION_TTL)
            
        Returns:
            True if session was refreshed, False if session doesn't exist
        """
        key = self.generate_session_key(session_id)
        ttl = ttl or self.SESSION_TTL
        
        # Check if session exists
        exists = await self.redis.exists(key)
        if not exists:
            return False
        
        # Update expiration
        await self.redis.expire(key, ttl)
        
        # Update expires_at in session data
        session_data = await self.get_session(session_id)
        if session_data:
            session_data["expires_at"] = (
                datetime.utcnow() + timedelta(seconds=ttl)
            ).isoformat()
            session_json = json.dumps(session_data, default=str)
            await self.redis.setex(key, ttl, session_json)
        
        return True
    
    # ========================================================================
    # Refresh Token Management
    # ========================================================================
    
    async def store_refresh_token(
        self,
        token_hash: str,
        user_id: UUID,
        ttl: Optional[int] = None
    ) -> None:
        """
        Store refresh token mapping.
        
        Args:
            token_hash: Hashed refresh token
            user_id: User identifier
            ttl: Time to live in seconds (default: SESSION_TTL)
        """
        key = self.generate_refresh_token_key(token_hash)
        ttl = ttl or self.SESSION_TTL
        
        # Store user_id as value
        await self.redis.setex(key, ttl, str(user_id))
    
    async def get_refresh_token_user(self, token_hash: str) -> Optional[UUID]:
        """
        Get user ID from refresh token.
        
        Args:
            token_hash: Hashed refresh token
            
        Returns:
            User ID if token is valid, None otherwise
        """
        key = self.generate_refresh_token_key(token_hash)
        user_id_str = await self.redis.get(key)
        
        if user_id_str:
            return UUID(user_id_str)
        
        return None
    
    async def delete_refresh_token(self, token_hash: str) -> None:
        """
        Delete refresh token (logout).
        
        Args:
            token_hash: Hashed refresh token
        """
        key = self.generate_refresh_token_key(token_hash)
        await self.redis.delete(key)
    
    # ========================================================================
    # Generic Cache Operations
    # ========================================================================
    
    async def get(self, key: str) -> Optional[str]:
        """Generic get operation"""
        return await self.redis.get(key)
    
    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None
    ) -> None:
        """Generic set operation"""
        if ttl:
            await self.redis.setex(key, ttl, value)
        else:
            await self.redis.set(key, value)
    
    async def delete(self, key: str) -> None:
        """Generic delete operation"""
        await self.redis.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return bool(await self.redis.exists(key))
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "cache:*")
            
        Returns:
            Number of keys deleted
        """
        cursor = 0
        deleted_count = 0
        
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            
            if keys:
                await self.redis.delete(*keys)
                deleted_count += len(keys)
            
            if cursor == 0:
                break
        
        return deleted_count
