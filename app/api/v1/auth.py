"""Authentication API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis
from uuid import uuid4, UUID
from datetime import datetime
from typing import List
from app.core.database import get_db, get_redis
from app.services.auth_service import AuthService
from app.schemas.auth import LoginRequest, Token, RefreshTokenRequest
from app.schemas.user import UserCreate, User
from app.schemas.api_key import APIKeyCreate, APIKey, APIKeyResponse
from app.models.user import UserModel
from app.models.api_key import APIKeyModel
from app.core.security import hash_password, generate_api_key, hash_api_key
from app.api.middleware import limiter
from app.core.config import settings


router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


async def get_auth_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> AuthService:
    """Dependency to get AuthService instance"""
    return AuthService(db_session=db, cache=redis)


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user.
    
    Creates a new user account with the provided credentials.
    Password is hashed using bcrypt before storage.
    Includes comprehensive error handling for role validation.
    
    Args:
        request: FastAPI request object (for rate limiting)
        user_data: User registration data (username, email, password, role)
        db: Database session
        
    Returns:
        Created user object (without password)
        
    Raises:
        HTTPException 400: If username/email already exists or role validation fails
        HTTPException 422: If input validation fails
    """
    from app.core.exceptions import RoleValidationError
    from app.core.logging_config import get_logger
    
    logger = get_logger(__name__)
    
    try:
        # Check if username already exists
        from sqlalchemy import select
        stmt = select(UserModel).where(UserModel.username == user_data.username)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            logger.warning(
                "registration_failed_username_exists",
                username=user_data.username,
                context="auth.register"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        stmt = select(UserModel).where(UserModel.email == user_data.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            logger.warning(
                "registration_failed_email_exists",
                email=user_data.email,
                context="auth.register"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        user = UserModel(
            id=str(uuid4()),  # Convert UUID to string for SQLite compatibility
            username=user_data.username,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            role=user_data.role,
            is_active=True
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info(
            "user_registered_successfully",
            user_id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role.value,
            context="auth.register"
        )
        
        return user
        
    except RoleValidationError as e:
        # Handle role validation errors with detailed response
        logger.error(
            "registration_failed_role_validation",
            username=user_data.username,
            email=user_data.email,
            invalid_role=e.invalid_role,
            valid_roles=e.valid_roles,
            context="auth.register",
            error_details=e.details,
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.get_api_response()
        )
    
    except Exception as e:
        # Handle unexpected errors
        logger.error(
            "registration_failed_unexpected_error",
            username=user_data.username,
            email=user_data.email,
            error_type=type(e).__name__,
            error_message=str(e),
            context="auth.register",
            exc_info=True
        )
        
        # Don't expose internal errors to the client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )


@router.post("/login", response_model=Token)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def login(
    request: Request,
    credentials: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    User login with JWT generation.
    
    Authenticates user with username/email and password.
    Includes role validation and normalization for backward compatibility.
    Returns access token and refresh token on success.
    
    Args:
        request: FastAPI request object (for rate limiting)
        credentials: Login credentials (username/email and password)
        auth_service: Authentication service
        
    Returns:
        Token object with access_token, refresh_token, and expiry
        
    Raises:
        HTTPException 401: If credentials are invalid
        HTTPException 500: If token creation fails
    """
    from app.core.exceptions import RoleValidationError, AuthenticationError, TokenValidationError
    from app.core.logging_config import get_logger
    
    logger = get_logger(__name__)
    
    try:
        # Authenticate user with role validation and normalization
        user = await auth_service.authenticate_with_role_validation(
            username=credentials.username,
            password=credentials.password
        )
        
        if user is None:
            logger.warning(
                "login_failed_invalid_credentials",
                username=credentials.username,
                context="auth.login"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Create tokens with normalized role
        access_token, refresh_token, expires_in = await auth_service.create_tokens(user)
        
        logger.info(
            "login_successful",
            user_id=str(user.id),
            username=user.username,
            role=user.role.value,
            context="auth.login"
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in
        )
        
    except (RoleValidationError, AuthenticationError, TokenValidationError) as e:
        # Handle authentication-related errors
        logger.error(
            "login_failed_auth_error",
            username=credentials.username,
            error_type=type(e).__name__,
            error_message=str(e),
            context="auth.login",
            exc_info=True
        )
        
        # For security, don't expose detailed error information
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    except Exception as e:
        # Handle unexpected errors
        logger.error(
            "login_failed_unexpected_error",
            username=credentials.username,
            error_type=type(e).__name__,
            error_message=str(e),
            context="auth.login",
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token.
    
    Exchanges a valid refresh token for a new access token.
    The refresh token remains valid and can be reused.
    
    Args:
        token_request: Refresh token request
        auth_service: Authentication service
        
    Returns:
        Token object with new access_token and same refresh_token
        
    Raises:
        HTTPException 401: If refresh token is invalid or expired
    """
    # Refresh access token
    result = await auth_service.refresh_access_token(token_request.refresh_token)
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token, expires_in = result
    
    return Token(
        access_token=access_token,
        refresh_token=token_request.refresh_token,  # Return same refresh token
        token_type="bearer",
        expires_in=expires_in
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token_request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Invalidate refresh token (logout).
    
    Revokes the provided refresh token, effectively logging out the user.
    The access token will continue to work until it expires naturally.
    
    Args:
        token_request: Refresh token to revoke
        auth_service: Authentication service
        
    Returns:
        No content (204)
    """
    await auth_service.revoke_refresh_token(token_request.refresh_token)
    return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserModel:
    """
    Dependency to get current authenticated user from JWT token.
    
    Includes role validation and normalization for backward compatibility.
    Provides comprehensive error handling and logging.
    
    Args:
        credentials: HTTP Bearer token credentials
        auth_service: Authentication service
        
    Returns:
        Current authenticated user with normalized role
        
    Raises:
        HTTPException 401: If token is invalid or expired
    """
    from app.core.exceptions import RoleValidationError, TokenValidationError, BackwardCompatibilityError
    from app.core.logging_config import get_logger
    
    logger = get_logger(__name__)
    
    try:
        token = credentials.credentials
        payload = await auth_service.verify_access_token(token)
        
        if payload is None:
            logger.warning(
                "token_verification_failed",
                context="auth.get_current_user"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Get user from database
        user_id = UUID(payload.get("user_id"))
        db = auth_service.db
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None or not user.is_active:
            logger.warning(
                "user_not_found_or_inactive",
                user_id=str(user_id),
                context="auth.get_current_user"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Validate and normalize user role for consistency
        user = await auth_service.validate_and_normalize_user_role(user)
        
        # Validate role consistency between token and database for security
        # This ensures backward compatibility while maintaining security
        from app.core.security import extract_role_from_token
        token_role = extract_role_from_token(payload)
        
        if token_role is not None and token_role != user.role:
            # Log potential security issue but don't fail authentication
            # The database is the source of truth for current user roles
            compatibility_error = BackwardCompatibilityError(
                message=f"Role mismatch for user {user.id}: token={token_role.value}, db={user.role.value}",
                compatibility_issue="token_role_mismatch",
                user_id=str(user.id),
                details={
                    "token_role": token_role.value,
                    "database_role": user.role.value
                }
            )
            
            logger.warning(
                "token_role_mismatch_detected",
                **compatibility_error.to_dict(),
                context="auth.get_current_user"
            )
        
        logger.debug(
            "user_authenticated_successfully",
            user_id=str(user.id),
            username=user.username,
            role=user.role.value,
            context="auth.get_current_user"
        )
        
        return user
        
    except (RoleValidationError, TokenValidationError) as e:
        # Handle authentication-related errors
        logger.error(
            "authentication_failed_validation_error",
            error_type=type(e).__name__,
            error_message=str(e),
            context="auth.get_current_user",
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    except Exception as e:
        # Handle unexpected errors
        logger.error(
            "authentication_failed_unexpected_error",
            error_type=type(e).__name__,
            error_message=str(e),
            context="auth.get_current_user",
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new API key.
    
    Generates a secure API key for the authenticated user.
    The plain API key is only returned once at creation time.
    
    Args:
        key_data: API key creation data (name, optional expiry)
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        Created API key with the plain key value
        
    Raises:
        HTTPException 401: If user is not authenticated
    """
    # Generate API key
    plain_key = generate_api_key()
    key_hash = hash_api_key(plain_key)
    
    # Create API key record
    api_key = APIKeyModel(
        id=str(uuid4()),  # Convert UUID to string for SQLite compatibility
        user_id=current_user.id,
        key_hash=key_hash,
        name=key_data.name,
        expires_at=key_data.expires_at
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    # Return response with plain key
    return APIKeyResponse(
        id=api_key.id,
        user_id=api_key.user_id,
        name=api_key.name,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        revoked_at=api_key.revoked_at,
        created_at=api_key.created_at,
        updated_at=api_key.updated_at,
        key=plain_key  # Only shown once
    )


@router.get("/api-keys", response_model=List[APIKey])
async def list_api_keys(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List user's API keys.
    
    Returns all API keys belonging to the authenticated user.
    Does not include the actual key values.
    
    Args:
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        List of API keys (without plain key values)
        
    Raises:
        HTTPException 401: If user is not authenticated
    """
    stmt = select(APIKeyModel).where(
        APIKeyModel.user_id == current_user.id
    ).order_by(APIKeyModel.created_at.desc())
    
    result = await db.execute(stmt)
    api_keys = result.scalars().all()
    
    return api_keys


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke an API key.
    
    Marks the specified API key as revoked, preventing further use.
    Users can only revoke their own API keys.
    
    Args:
        key_id: ID of the API key to revoke
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        No content (204)
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 404: If API key not found or doesn't belong to user
    """
    stmt = select(APIKeyModel).where(
        APIKeyModel.id == key_id,
        APIKeyModel.user_id == current_user.id
    )
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()
    
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Mark as revoked
    api_key.revoked_at = datetime.utcnow()
    await db.commit()
    
    return None
