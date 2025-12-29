"""Common API dependencies for authentication and authorization"""

from functools import wraps
from typing import Callable, List
from fastapi import Depends, HTTPException, status
from app.models.user import UserModel
from app.api.v1.auth import get_current_user
from app.core.permissions import check_permission


def require_permission(resource: str, action: str):
    """
    Decorator to require specific permission for an endpoint.
    
    Args:
        resource: Resource name (e.g., "mcps", "knowledge")
        action: Action name (e.g., "create", "read", "update", "delete")
        
    Returns:
        Decorator function that checks permissions
        
    Raises:
        HTTPException 403: If user lacks required permission
        
    Example:
        @router.post("/mcps")
        @require_permission("mcps", "create")
        async def create_mcp_tool(...):
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: UserModel = Depends(get_current_user), **kwargs):
            # Check if user has permission
            if not check_permission(current_user.role, resource, action):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User lacks permission: {resource}:{action}"
                )
            
            # Call the original function
            return await func(*args, current_user=current_user, **kwargs)
        
        return wrapper
    return decorator


def require_any_permission(permissions: List[str]):
    """
    Decorator to require any of the specified permissions for an endpoint.
    
    Args:
        permissions: List of permission strings (format: "resource:action")
        
    Returns:
        Decorator function that checks permissions
        
    Raises:
        HTTPException 403: If user lacks all specified permissions
        
    Example:
        @router.get("/admin/stats")
        @require_any_permission(["admin:read", "stats:read"])
        async def get_stats(...):
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: UserModel = Depends(get_current_user), **kwargs):
            # Check if user has any of the permissions
            has_permission = False
            for permission in permissions:
                parts = permission.split(":")
                if len(parts) == 2:
                    resource, action = parts
                    if check_permission(current_user.role, resource, action):
                        has_permission = True
                        break
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User lacks required permissions: {', '.join(permissions)}"
                )
            
            # Call the original function
            return await func(*args, current_user=current_user, **kwargs)
        
        return wrapper
    return decorator


def require_all_permissions(permissions: List[str]):
    """
    Decorator to require all of the specified permissions for an endpoint.
    
    Args:
        permissions: List of permission strings (format: "resource:action")
        
    Returns:
        Decorator function that checks permissions
        
    Raises:
        HTTPException 403: If user lacks any of the specified permissions
        
    Example:
        @router.post("/admin/critical-action")
        @require_all_permissions(["admin:write", "critical:execute"])
        async def critical_action(...):
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: UserModel = Depends(get_current_user), **kwargs):
            # Check if user has all permissions
            for permission in permissions:
                parts = permission.split(":")
                if len(parts) == 2:
                    resource, action = parts
                    if not check_permission(current_user.role, resource, action):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"User lacks required permission: {permission}"
                        )
            
            # Call the original function
            return await func(*args, current_user=current_user, **kwargs)
        
        return wrapper
    return decorator
