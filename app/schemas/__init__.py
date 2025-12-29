"""Pydantic schemas for API request/response validation"""

from app.schemas.mcp_tool import (
    MCPToolCreate,
    MCPToolUpdate,
    MCPTool,
    MCPToolVersion,
    ToolStatus
)
from app.schemas.knowledge import (
    DocumentCreate,
    DocumentUpdate,
    Document,
    SearchResult,
    SearchQuery
)
from app.schemas.ai_analysis import (
    FeasibilityReport,
    Improvement,
    ConfigRequirements,
    AnalysisRequest
)
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    User,
    UserRole
)
from app.schemas.auth import (
    Token,
    TokenPayload,
    LoginRequest,
    RefreshTokenRequest
)
from app.schemas.api_key import (
    APIKeyCreate,
    APIKey,
    APIKeyResponse
)
from app.schemas.common import (
    Pagination,
    Page,
    ErrorResponse,
    HealthCheck
)

__all__ = [
    # MCP Tool schemas
    "MCPToolCreate",
    "MCPToolUpdate",
    "MCPTool",
    "MCPToolVersion",
    "ToolStatus",
    # Knowledge schemas
    "DocumentCreate",
    "DocumentUpdate",
    "Document",
    "SearchResult",
    "SearchQuery",
    # AI Analysis schemas
    "FeasibilityReport",
    "Improvement",
    "ConfigRequirements",
    "AnalysisRequest",
    # User schemas
    "UserCreate",
    "UserUpdate",
    "User",
    "UserRole",
    # Auth schemas
    "Token",
    "TokenPayload",
    "LoginRequest",
    "RefreshTokenRequest",
    # API Key schemas
    "APIKeyCreate",
    "APIKey",
    "APIKeyResponse",
    # Common schemas
    "Pagination",
    "Page",
    "ErrorResponse",
    "HealthCheck",
]
