"""Security utilities for password hashing and verification"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
import uuid
import secrets
import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.models.user import UserRole

# Password hashing context using bcrypt
# Configure to use bcrypt backend explicitly and avoid the wrap bug detection
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__default_rounds=12,
    bcrypt__default_ident="2b"
)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
    
    Note:
        Bcrypt has a 72-byte limit. Passwords are truncated if necessary.
    """
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        password = password_bytes.decode('utf-8', errors='ignore')
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hashed password.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    
    Note:
        Bcrypt has a 72-byte limit. Passwords are truncated if necessary.
    """
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        plain_password = password_bytes.decode('utf-8', errors='ignore')
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: UUID,
    username: str,
    role: UserRole,
    permissions: list[str],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token with user claims.
    
    Args:
        user_id: User's unique identifier
        username: User's username
        role: User's role
        permissions: List of user permissions
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Ensure role is always stored as lowercase string for consistency
    # This handles both UserRole enum values and any string inputs
    if isinstance(role, UserRole):
        role_claim = role.value  # Already lowercase from enum definition
    else:
        # Handle case where role might be passed as string (backward compatibility)
        role_claim = str(role).lower()
    
    # Create token payload with claims
    to_encode = {
        "sub": str(user_id),  # Subject (standard JWT claim)
        "user_id": str(user_id),
        "username": username,
        "role": role_claim,  # Always lowercase for consistency
        "permissions": permissions,
        "exp": expire,  # Expiration time (standard JWT claim)
        "iat": datetime.utcnow(),  # Issued at (standard JWT claim)
        "jti": str(uuid.uuid4())  # JWT ID for tracking
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    user_id: UUID,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: User's unique identifier
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    to_encode = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4())
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a JWT token and return its payload.
    
    Args:
        token: JWT token string to verify
        
    Returns:
        Token payload if valid and not expired, None otherwise
    """
    payload = decode_token(token)
    if payload is None:
        return None
    
    # Check expiration
    exp = payload.get("exp")
    if exp is None:
        return None
    
    # Convert exp to datetime if it's a timestamp
    if isinstance(exp, (int, float)):
        exp_datetime = datetime.fromtimestamp(exp)
    else:
        exp_datetime = exp
    
    if exp_datetime < datetime.utcnow():
        return None
    
    # Handle backward compatibility for role claims
    # Normalize role claim to lowercase for consistency
    if "role" in payload:
        role_claim = payload["role"]
        if isinstance(role_claim, str):
            # Normalize to lowercase for consistent handling
            payload["role"] = role_claim.lower()
    
    return payload


def generate_api_key() -> str:
    """
    Generate a secure random API key.
    
    Returns:
        A secure random API key string (64 characters)
    """
    # Generate 32 random bytes and convert to hex (64 characters)
    return secrets.token_hex(32)


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256.
    
    Args:
        api_key: Plain API key to hash
        
    Returns:
        Hashed API key string
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against a hashed key.
    
    Args:
        plain_key: Plain API key to verify
        hashed_key: Hashed API key to compare against
        
    Returns:
        True if API key matches, False otherwise
    """
    return hash_api_key(plain_key) == hashed_key


def extract_role_from_token(payload: Dict[str, Any]) -> Optional[UserRole]:
    """
    Extract and normalize role from JWT token payload.
    
    Handles backward compatibility by accepting both uppercase and lowercase
    role claims from existing tokens.
    
    Args:
        payload: JWT token payload dictionary
        
    Returns:
        UserRole enum if valid role found, None otherwise
    """
    role_claim = payload.get("role")
    if role_claim is None:
        return None
    
    try:
        # Use UserRole.normalize to handle case-insensitive conversion
        return UserRole.normalize(role_claim)
    except ValueError:
        # Invalid role in token, return None
        return None
