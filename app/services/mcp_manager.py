"""MCP Manager Service - Handles CRUD operations for MCP tools"""

import json
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import select, update, delete as sql_delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.models.mcp_tool import MCPToolModel, ToolStatus
from app.schemas.mcp_tool import (
    MCPToolCreate,
    MCPToolUpdate,
    MCPTool,
    MCPToolVersion
)


class MCPToolFilters:
    """Filters for listing MCP tools"""
    def __init__(
        self,
        status: Optional[ToolStatus] = None,
        author_id: Optional[UUID] = None,
        search: Optional[str] = None
    ):
        self.status = status
        self.author_id = author_id
        self.search = search


class Pagination:
    """Pagination parameters"""
    def __init__(self, page: int = 1, page_size: int = 20):
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), 100)  # Max 100 items per page
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size


class Page:
    """Paginated response"""
    def __init__(
        self,
        items: List[Any],
        total: int,
        page: int,
        page_size: int
    ):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    def dict(self) -> Dict[str, Any]:
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages
        }


class MCPManager:
    """
    MCP Manager handles CRUD operations for MCP tools.
    
    Responsibilities:
    - Create, read, update, delete MCP tools
    - Version history management
    - Caching for performance
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        mongo_db: AsyncIOMotorDatabase,
        cache: Redis
    ):
        self.db = db_session
        self.mongo = mongo_db
        self.cache = cache
        self.history_collection = mongo_db["mcp_config_history"]
    
    # ========================================================================
    # CRUD Operations
    # ========================================================================
    
    async def create_tool(self, tool_data: MCPToolCreate) -> MCPTool:
        """
        Create a new MCP tool.
        
        Args:
            tool_data: Tool creation data
            
        Returns:
            Created MCP tool
            
        Raises:
            ValueError: If slug already exists
        """
        # Check if slug already exists
        existing = await self._get_tool_by_slug(tool_data.slug)
        if existing:
            raise ValueError(f"Tool with slug '{tool_data.slug}' already exists")
        
        # Create new tool model
        tool_model = MCPToolModel(
            id=str(uuid4()),
            name=tool_data.name,
            slug=tool_data.slug,
            description=tool_data.description,
            version=tool_data.version,
            author_id=str(tool_data.author_id),
            status=tool_data.status or ToolStatus.DRAFT,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Insert into MySQL
        self.db.add(tool_model)
        await self.db.flush()
        await self.db.refresh(tool_model)
        
        # Store initial version in MongoDB
        await self._store_version_history(
            tool_id=UUID(tool_model.id),
            version=tool_data.version,
            config=tool_data.config,
            changed_by=tool_data.author_id,
            change_type="create"
        )
        
        # Convert to Pydantic model
        tool = MCPTool.model_validate(tool_model)
        
        # Cache the tool
        await self._cache_tool(tool)
        
        return tool
    
    async def get_tool(self, tool_id: UUID) -> Optional[MCPTool]:
        """
        Get an MCP tool by ID with caching.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            MCP tool if found, None otherwise
        """
        # Try cache first
        cached_tool = await self._get_cached_tool(tool_id)
        if cached_tool:
            return cached_tool
        
        # Query database
        stmt = select(MCPToolModel).where(
            MCPToolModel.id == str(tool_id),
            MCPToolModel.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        tool_model = result.scalar_one_or_none()
        
        if not tool_model:
            return None
        
        # Convert to Pydantic model
        tool = MCPTool.model_validate(tool_model)
        
        # Cache the tool
        await self._cache_tool(tool)
        
        return tool
    
    async def update_tool(
        self,
        tool_id: UUID,
        updates: MCPToolUpdate
    ) -> MCPTool:
        """
        Update an MCP tool and store version history.
        
        Args:
            tool_id: Tool identifier
            updates: Update data
            
        Returns:
            Updated MCP tool
            
        Raises:
            ValueError: If tool not found or slug already exists
        """
        # Get existing tool
        stmt = select(MCPToolModel).where(
            MCPToolModel.id == str(tool_id),
            MCPToolModel.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        tool_model = result.scalar_one_or_none()
        
        if not tool_model:
            raise ValueError(f"Tool with ID '{tool_id}' not found")
        
        # Note: slug is not updatable in MCPToolUpdate schema
        
        # Store previous version in MongoDB before updating
        if updates.config:
            # Get previous config from MongoDB
            previous_config = await self._get_latest_config(tool_id)
            
            await self._store_version_history(
                tool_id=tool_id,
                version=tool_model.version,
                config=previous_config or {},
                changed_by=UUID(tool_model.author_id),
                change_type="update"
            )
        
        # Update fields
        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(tool_model, field):
                setattr(tool_model, field, value)
        
        tool_model.updated_at = datetime.utcnow()
        
        # Commit changes
        await self.db.flush()
        await self.db.refresh(tool_model)
        
        # Store new config version if provided
        if updates.config:
            await self._store_version_history(
                tool_id=tool_id,
                version=updates.version or tool_model.version,
                config=updates.config,
                changed_by=UUID(tool_model.author_id),
                change_type="update"
            )
        
        # Convert to Pydantic model
        tool = MCPTool.model_validate(tool_model)
        
        # Invalidate cache
        await self._invalidate_cache(tool_id)
        
        return tool
    
    async def delete_tool(self, tool_id: UUID) -> bool:
        """
        Soft delete an MCP tool.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            True if deleted, False if not found
        """
        # Get existing tool
        stmt = select(MCPToolModel).where(
            MCPToolModel.id == str(tool_id),
            MCPToolModel.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        tool_model = result.scalar_one_or_none()
        
        if not tool_model:
            return False
        
        # Get current config for history
        current_config = await self._get_latest_config(tool_id)
        
        # Soft delete (set deleted_at timestamp)
        tool_model.deleted_at = datetime.utcnow()
        tool_model.updated_at = datetime.utcnow()
        
        await self.db.flush()
        
        # Store deletion in MongoDB history
        await self._store_version_history(
            tool_id=tool_id,
            version=tool_model.version,
            config=current_config or {},
            changed_by=UUID(tool_model.author_id),
            change_type="delete"
        )
        
        # Invalidate cache
        await self._invalidate_cache(tool_id)
        
        return True
    
    async def list_tools(
        self,
        filters: MCPToolFilters,
        pagination: Pagination
    ) -> Page:
        """
        List MCP tools with filtering and pagination.
        
        Args:
            filters: Filter criteria
            pagination: Pagination parameters
            
        Returns:
            Paginated list of MCP tools
        """
        # Build query
        stmt = select(MCPToolModel).where(MCPToolModel.deleted_at.is_(None))
        
        # Apply filters
        if filters.status:
            stmt = stmt.where(MCPToolModel.status == filters.status)
        
        if filters.author_id:
            stmt = stmt.where(MCPToolModel.author_id == str(filters.author_id))
        
        if filters.search:
            search_pattern = f"%{filters.search}%"
            stmt = stmt.where(
                (MCPToolModel.name.like(search_pattern)) |
                (MCPToolModel.description.like(search_pattern)) |
                (MCPToolModel.slug.like(search_pattern))
            )
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()
        
        # Apply pagination
        stmt = stmt.offset(pagination.offset).limit(pagination.limit)
        
        # Execute query
        result = await self.db.execute(stmt)
        tool_models = result.scalars().all()
        
        # Convert to Pydantic models
        tools = [MCPTool.model_validate(model) for model in tool_models]
        
        return Page(
            items=tools,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
    
    # ========================================================================
    # Version History Management
    # ========================================================================
    
    async def get_tool_history(self, tool_id: UUID) -> List[MCPToolVersion]:
        """
        Get version history for an MCP tool.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            List of version history entries in chronological order
        """
        cursor = self.history_collection.find(
            {"tool_id": str(tool_id)}
        ).sort("changed_at", 1)  # Ascending order (oldest first)
        
        history = []
        async for doc in cursor:
            history.append(MCPToolVersion(
                tool_id=UUID(doc["tool_id"]),
                version=doc["version"],
                config=doc["config"],
                changed_by=UUID(doc["changed_by"]),
                changed_at=doc["changed_at"],
                change_type=doc["change_type"],
                diff=doc.get("diff")
            ))
        
        return history
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    async def _get_tool_by_slug(self, slug: str) -> Optional[MCPToolModel]:
        """Get tool by slug"""
        stmt = select(MCPToolModel).where(
            MCPToolModel.slug == slug,
            MCPToolModel.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _store_version_history(
        self,
        tool_id: UUID,
        version: str,
        config: Dict[str, Any],
        changed_by: UUID,
        change_type: str,
        diff: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store version history in MongoDB"""
        document = {
            "tool_id": str(tool_id),
            "version": version,
            "config": config,
            "changed_by": str(changed_by),
            "changed_at": datetime.utcnow(),
            "change_type": change_type,
            "diff": diff
        }
        await self.history_collection.insert_one(document)
    
    async def _get_latest_config(self, tool_id: UUID) -> Optional[Dict[str, Any]]:
        """Get the latest config from MongoDB history"""
        doc = await self.history_collection.find_one(
            {"tool_id": str(tool_id)},
            sort=[("changed_at", -1)]  # Descending order (newest first)
        )
        return doc["config"] if doc else None
    
    async def _cache_tool(self, tool: MCPTool) -> None:
        """Cache tool in Redis"""
        cache_key = f"cache:mcp_tool:{tool.id}"
        tool_json = tool.model_dump_json()
        await self.cache.setex(cache_key, 3600, tool_json)  # 1 hour TTL
    
    async def _get_cached_tool(self, tool_id: UUID) -> Optional[MCPTool]:
        """Get tool from cache"""
        cache_key = f"cache:mcp_tool:{tool_id}"
        cached_data = await self.cache.get(cache_key)
        
        if cached_data:
            return MCPTool.model_validate_json(cached_data)
        
        return None
    
    async def _invalidate_cache(self, tool_id: UUID) -> None:
        """Invalidate tool cache"""
        cache_key = f"cache:mcp_tool:{tool_id}"
        await self.cache.delete(cache_key)
