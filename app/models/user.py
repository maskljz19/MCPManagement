"""User model"""

import enum
from sqlalchemy import Column, String, Boolean, Enum, Index
from sqlalchemy.orm import relationship, validates
from passlib.context import CryptContext
from app.models.base import BaseModel

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, enum.Enum):
    """User role for RBAC"""
    ADMIN = "ADMIN"
    DEVELOPER = "DEVELOPER"
    VIEWER = "VIEWER"
    
    @classmethod
    def normalize(cls, value: str) -> 'UserRole':
        """
        Normalize role value to proper enum, case-insensitive.
        
        Args:
            value: Role value as string (any case) or existing UserRole enum
            
        Returns:
            UserRole enum value
            
        Raises:
            RoleValidationError: If the role value is invalid
        """
        from app.core.exceptions import RoleValidationError
        
        if isinstance(value, cls):
            return value
        
        if not isinstance(value, str):
            valid_roles = [role.value for role in cls]
            raise RoleValidationError(
                invalid_role=str(value),
                valid_roles=valid_roles,
                context="Role normalization",
                details={"provided_type": type(value).__name__}
            )
        
        # Handle case-insensitive lookup by enum value
        normalized = value.lower().strip()
        for role in cls:
            if role.value == normalized:
                return role
        
        # Try uppercase enum name lookup (e.g., "ADMIN" -> UserRole.ADMIN)
        try:
            return cls[value.upper().strip()]
        except KeyError:
            pass
            
        valid_roles = [role.value for role in cls]
        raise RoleValidationError(
            invalid_role=value,
            valid_roles=valid_roles,
            context="Role normalization",
            details={"normalized_value": normalized}
        )
    
    def __str__(self) -> str:
        """Always serialize as lowercase value for consistent output"""
        return self.value


class UserModel(BaseModel):
    """
    User model for authentication and authorization.
    
    Stores user credentials with bcrypt password hashing.
    Implements role-based access control (RBAC).
    """
    __tablename__ = "users"
    
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        Enum(UserRole, values_callable=lambda obj: [e.value for e in obj]),
        default=UserRole.VIEWER,
        nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    api_keys = relationship(
        "APIKeyModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    github_connections = relationship(
        "GitHubConnectionModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    execution_queue = relationship(
        "ExecutionQueueModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    batch_executions = relationship(
        "BatchExecutionModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    scheduled_executions = relationship(
        "ScheduledExecutionModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    execution_costs = relationship(
        "ExecutionCostModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    resource_quota = relationship(
        "ResourceQuotaModel",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
    )
    
    def set_password(self, password: str) -> None:
        """Hash and set the user's password"""
        self.password_hash = pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash"""
        return pwd_context.verify(password, self.password_hash)
    
    @validates('role')
    def validate_role(self, key, role):
        """
        Ensure role is properly normalized before database operations.
        
        This validator ensures that any role assignment (whether from API,
        direct database operations, or migrations) goes through normalization
        to maintain consistency. Provides graceful degradation for edge cases.
        
        Args:
            key: The field name ('role')
            role: The role value to validate and normalize
            
        Returns:
            UserRole: Normalized role enum value
            
        Raises:
            RoleValidationError: If the role value is invalid and cannot be gracefully handled
        """
        from app.core.exceptions import RoleValidationError, BackwardCompatibilityError
        from app.core.logging_config import get_logger
        
        logger = get_logger(__name__)
        
        # Handle None values with default role
        if role is None:
            logger.info(
                "role_defaulted_to_viewer",
                context="UserModel.validate_role",
                reason="null_role_provided"
            )
            return UserRole.VIEWER
        
        # Handle existing UserRole enum values
        if isinstance(role, UserRole):
            return role
        
        # Handle string values through normalization
        if isinstance(role, str):
            try:
                normalized_role = UserRole.normalize(role)
                
                # Log if normalization changed the case (backward compatibility)
                if role != normalized_role.value:
                    logger.info(
                        "role_normalized",
                        original_role=role,
                        normalized_role=normalized_role.value,
                        context="UserModel.validate_role"
                    )
                
                return normalized_role
                
            except RoleValidationError as e:
                # Log the validation error with context
                logger.error(
                    "role_validation_failed",
                    invalid_role=role,
                    valid_roles=e.valid_roles,
                    context="UserModel.validate_role",
                    error_details=e.details,
                    exc_info=True
                )
                
                # For database operations, we might want to be more lenient
                # and provide graceful degradation in some cases
                if hasattr(self, '_allow_role_degradation') and self._allow_role_degradation:
                    logger.warning(
                        "role_degraded_to_viewer",
                        invalid_role=role,
                        reason="graceful_degradation_enabled",
                        context="UserModel.validate_role"
                    )
                    return UserRole.VIEWER
                
                # Re-raise the exception for strict validation
                raise
        
        # Handle other types by attempting string conversion
        try:
            string_role = str(role)
            logger.warning(
                "role_type_converted",
                original_type=type(role).__name__,
                converted_value=string_role,
                context="UserModel.validate_role"
            )
            
            return UserRole.normalize(string_role)
            
        except (RoleValidationError, Exception) as e:
            # Log the error and provide graceful degradation
            logger.error(
                "role_validation_failed_with_type_conversion",
                role_value=str(role),
                role_type=type(role).__name__,
                context="UserModel.validate_role",
                exc_info=True
            )
            
            # For backward compatibility, default to VIEWER for unrecognized types
            if hasattr(self, '_allow_role_degradation') and self._allow_role_degradation:
                logger.warning(
                    "role_degraded_to_viewer",
                    invalid_role=str(role),
                    reason="type_conversion_failed",
                    context="UserModel.validate_role"
                )
                return UserRole.VIEWER
            
            # Create a more specific error for non-string types
            from app.core.exceptions import RoleValidationError
            valid_roles = [role.value for role in UserRole]
            raise RoleValidationError(
                invalid_role=str(role),
                valid_roles=valid_roles,
                context="UserModel.validate_role",
                details={
                    "provided_type": type(role).__name__,
                    "conversion_attempted": True
                }
            )
    
    def enable_role_degradation(self):
        """
        Enable graceful role degradation for backward compatibility.
        
        When enabled, invalid roles will be degraded to VIEWER instead
        of raising exceptions. This is useful for data migrations and
        backward compatibility scenarios.
        
        **Requirements: 4.1, 4.3**
        """
        self._allow_role_degradation = True
    
    def disable_role_degradation(self):
        """
        Disable graceful role degradation (default behavior).
        
        When disabled, invalid roles will raise RoleValidationError
        exceptions for strict validation.
        """
        self._allow_role_degradation = False
    
    def has_role(self, required_role: str) -> bool:
        """
        Check if user has the specified role (case-insensitive).
        
        Args:
            required_role: Role to check against (any case format)
            
        Returns:
            bool: True if user has the required role
        """
        from app.core.exceptions import RoleValidationError
        from app.core.logging_config import get_logger
        
        try:
            normalized_required = UserRole.normalize(required_role)
            return self.role == normalized_required
        except RoleValidationError as e:
            # Log the validation error but don't fail the check
            logger = get_logger(__name__)
            logger.warning(
                "role_check_failed",
                user_id=str(self.id),
                required_role=required_role,
                user_role=self.role.value,
                error_message=str(e),
                context="UserModel.has_role"
            )
            return False
    
    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == UserRole.ADMIN
    
    def is_developer(self) -> bool:
        """Check if user has developer role"""
        return self.role == UserRole.DEVELOPER
    
    def is_viewer(self) -> bool:
        """Check if user has viewer role"""
        return self.role == UserRole.VIEWER
    
    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, username={self.username}, role={self.role})>"
