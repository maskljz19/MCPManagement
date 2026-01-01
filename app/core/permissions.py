"""Role-Based Access Control (RBAC) permission system"""

from typing import List
from app.models.user import UserRole


# Define role-permission mappings
# Format: "resource:action"
# Wildcard "*" means all resources or all actions
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        "*:*"  # Admin has all permissions
    ],
    UserRole.DEVELOPER: [
        "mcps:create",
        "mcps:read",
        "mcps:update",
        "mcps:delete",
        "knowledge:create",
        "knowledge:read",
        "knowledge:update",
        "knowledge:delete",
        "deployments:create",
        "deployments:read",
        "deployments:update",
        "deployments:delete",
        "github:create",
        "github:read",
        "github:update",
        "github:delete",
        "analyze:create",
        "analyze:read",
        "tasks:read",
        "tasks:delete"
    ],
    UserRole.VIEWER: [
        "mcps:read",
        "knowledge:read",
        "deployments:read",
        "tasks:read"
    ]
}


def get_permissions_for_role(role: UserRole) -> List[str]:
    """
    Get all permissions for a given role.
    
    Args:
        role: User role
        
    Returns:
        List of permission strings for the role
    """
    return ROLE_PERMISSIONS.get(role, [])


def check_permission(role: UserRole, resource: str, action: str) -> bool:
    """
    Check if a role has permission to perform an action on a resource.
    
    Args:
        role: User role to check
        resource: Resource name (e.g., "mcps", "knowledge")
        action: Action name (e.g., "create", "read", "update", "delete")
        
    Returns:
        True if role has permission, False otherwise
    """
    permissions = get_permissions_for_role(role)
    
    # Check for wildcard permissions
    if "*:*" in permissions:
        return True
    
    # Check for resource wildcard (e.g., "mcps:*")
    if f"{resource}:*" in permissions:
        return True
    
    # Check for action wildcard (e.g., "*:read")
    if f"*:{action}" in permissions:
        return True
    
    # Check for exact permission match
    if f"{resource}:{action}" in permissions:
        return True
    
    return False


def has_any_permission(role: UserRole, permissions: List[str]) -> bool:
    """
    Check if a role has any of the specified permissions.
    
    Args:
        role: User role to check
        permissions: List of permission strings to check (format: "resource:action")
        
    Returns:
        True if role has at least one of the permissions, False otherwise
    """
    for permission in permissions:
        parts = permission.split(":")
        if len(parts) != 2:
            continue
        resource, action = parts
        if check_permission(role, resource, action):
            return True
    return False


def has_all_permissions(role: UserRole, permissions: List[str]) -> bool:
    """
    Check if a role has all of the specified permissions.
    
    Args:
        role: User role to check
        permissions: List of permission strings to check (format: "resource:action")
        
    Returns:
        True if role has all permissions, False otherwise
    """
    for permission in permissions:
        parts = permission.split(":")
        if len(parts) != 2:
            return False
        resource, action = parts
        if not check_permission(role, resource, action):
            return False
    return True
