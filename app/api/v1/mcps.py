"""MCP Tool Management API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis
from uuid import UUID
from typing import List, Optional

from app.core.database import get_db, get_mongodb, get_redis
from app.services.mcp_manager import MCPManager, MCPToolFilters, Pagination, Page
from app.schemas.mcp_tool import (
    MCPToolCreate,
    MCPToolUpdate,
    MCPTool,
    MCPToolVersion
)
from app.models.mcp_tool import ToolStatus
from app.models.user import UserModel
from app.api.v1.auth import get_current_user
from app.api.dependencies import require_permission


router = APIRouter(prefix="/mcps", tags=["MCP Tools"])


async def get_mcp_manager(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> MCPManager:
    """Dependency to get MCPManager instance"""
    mongo = get_mongodb()
    return MCPManager(db_session=db, mongo_db=mongo, cache=redis)


@router.post("", response_model=MCPTool, status_code=status.HTTP_201_CREATED)
@require_permission("mcps", "create")
async def create_mcp_tool(
    tool_data: MCPToolCreate,
    current_user: UserModel = Depends(get_current_user),
    mcp_manager: MCPManager = Depends(get_mcp_manager)
):
    """
    Create a new MCP tool.
    
    Creates a new MCP tool with the provided metadata and configuration.
    The tool is initially stored in MySQL and the configuration history
    is recorded in MongoDB.
    
    Args:
        tool_data: Tool creation data (name, slug, version, config, etc.)
        current_user: Currently authenticated user
        mcp_manager: MCP Manager service
        
    Returns:
        Created MCP tool object
        
    Raises:
        HTTPException 400: If slug already exists
        HTTPException 401: If user is not authenticated
        HTTPException 422: If validation fails
    """
    try:
        # Override author_id with current user
        tool_data.author_id = current_user.id
        
        # Create tool
        tool = await mcp_manager.create_tool(tool_data)
        return tool
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{tool_id}", response_model=MCPTool)
@require_permission("mcps", "read")
async def get_mcp_tool(
    tool_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    mcp_manager: MCPManager = Depends(get_mcp_manager)
):
    """
    Get MCP tool details by ID.
    
    Retrieves a specific MCP tool by its unique identifier.
    Results are cached in Redis for performance.
    
    Args:
        tool_id: Tool unique identifier
        current_user: Currently authenticated user
        mcp_manager: MCP Manager service
        
    Returns:
        MCP tool object
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 404: If tool not found
    """
    tool = await mcp_manager.get_tool(tool_id)
    
    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP tool with ID '{tool_id}' not found"
        )
    
    return tool


@router.put("/{tool_id}", response_model=MCPTool)
@require_permission("mcps", "update")
async def update_mcp_tool(
    tool_id: UUID,
    updates: MCPToolUpdate,
    current_user: UserModel = Depends(get_current_user),
    mcp_manager: MCPManager = Depends(get_mcp_manager)
):
    """
    Update an MCP tool.
    
    Updates an existing MCP tool with the provided changes.
    Previous version is stored in MongoDB history before updating.
    Cache is invalidated after successful update.
    
    Args:
        tool_id: Tool unique identifier
        updates: Update data (name, description, version, config, status)
        current_user: Currently authenticated user
        mcp_manager: MCP Manager service
        
    Returns:
        Updated MCP tool object
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 404: If tool not found
        HTTPException 422: If validation fails
    """
    try:
        tool = await mcp_manager.update_tool(tool_id, updates)
        return tool
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("mcps", "delete")
async def delete_mcp_tool(
    tool_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    mcp_manager: MCPManager = Depends(get_mcp_manager)
):
    """
    Delete an MCP tool (soft delete).
    
    Marks the MCP tool as deleted by setting the deleted_at timestamp.
    The tool record is preserved in the database and a deletion record
    is stored in MongoDB history.
    
    Args:
        tool_id: Tool unique identifier
        current_user: Currently authenticated user
        mcp_manager: MCP Manager service
        
    Returns:
        No content (204)
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 404: If tool not found
    """
    deleted = await mcp_manager.delete_tool(tool_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP tool with ID '{tool_id}' not found"
        )
    
    return None


@router.get("", response_model=dict)
@require_permission("mcps", "read")
async def list_mcp_tools(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    status: Optional[ToolStatus] = Query(None, description="Filter by tool status"),
    author_id: Optional[UUID] = Query(None, description="Filter by author ID"),
    search: Optional[str] = Query(None, description="Search in name, description, or slug"),
    current_user: UserModel = Depends(get_current_user),
    mcp_manager: MCPManager = Depends(get_mcp_manager)
):
    """
    List MCP tools with pagination and filtering.
    
    Returns a paginated list of MCP tools with optional filtering by status,
    author, or search query. Results are cached in Redis for performance.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        status: Optional filter by tool status (draft, active, deprecated)
        author_id: Optional filter by author ID
        search: Optional search query (searches name, description, slug)
        current_user: Currently authenticated user
        mcp_manager: MCP Manager service
        
    Returns:
        Paginated response with items, total, page, page_size, total_pages
        
    Raises:
        HTTPException 401: If user is not authenticated
    """
    # Create filters
    filters = MCPToolFilters(
        status=status,
        author_id=author_id,
        search=search
    )
    
    # Create pagination
    pagination = Pagination(page=page, page_size=page_size)
    
    # Get paginated results
    result = await mcp_manager.list_tools(filters, pagination)
    
    # Return as dict with serialized items matching frontend expectations
    return {
        "items": [tool.model_dump() for tool in result.items],
        "total": result.total,
        "page": result.page,
        "limit": result.page_size,  # Frontend expects 'limit' not 'page_size'
        "pages": result.total_pages  # Frontend expects 'pages' not 'total_pages'
    }


@router.get("/{tool_id}/history", response_model=List[MCPToolVersion])
@require_permission("mcps", "read")
async def get_tool_history(
    tool_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    mcp_manager: MCPManager = Depends(get_mcp_manager)
):
    """
    Get version history for an MCP tool.
    
    Returns all historical versions of the tool's configuration
    in chronological order (oldest first). History is stored in MongoDB.
    
    Args:
        tool_id: Tool unique identifier
        current_user: Currently authenticated user
        mcp_manager: MCP Manager service
        
    Returns:
        List of version history entries
        
    Raises:
        HTTPException 401: If user is not authenticated
    """
    history = await mcp_manager.get_tool_history(tool_id)
    return history
