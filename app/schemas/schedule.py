"""Schedule Schemas"""

from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator


class ScheduleCreateRequest(BaseModel):
    """Request schema for creating a scheduled execution"""
    tool_id: UUID = Field(..., description="ID of the tool to execute")
    tool_name: str = Field(..., description="Name of the tool")
    arguments: Dict[str, Any] = Field(..., description="Arguments to pass to the tool")
    schedule_expression: str = Field(
        ...,
        description="Cron expression for scheduling (e.g., '0 0 * * *' for daily at midnight)",
        example="0 0 * * *"
    )
    
    @validator('schedule_expression')
    def validate_cron_expression(cls, v):
        """Validate cron expression format"""
        from croniter import croniter
        try:
            croniter(v)
            return v
        except (ValueError, KeyError):
            raise ValueError(
                f"Invalid cron expression: {v}. "
                "Must be a valid cron expression (e.g., '0 0 * * *' for daily at midnight)."
            )


class ScheduleResponse(BaseModel):
    """Response schema for schedule information"""
    schedule_id: UUID = Field(..., description="Unique identifier for the schedule")
    tool_id: UUID = Field(..., description="ID of the tool to execute")
    user_id: UUID = Field(..., description="ID of the user who created the schedule")
    tool_name: str = Field(..., description="Name of the tool")
    arguments: Dict[str, Any] = Field(..., description="Arguments to pass to the tool")
    schedule_expression: str = Field(..., description="Cron expression for scheduling")
    next_execution_at: datetime = Field(..., description="Next scheduled execution time")
    last_execution_at: Optional[datetime] = Field(None, description="Last execution time")
    last_execution_status: Optional[str] = Field(None, description="Status of last execution")
    is_active: bool = Field(..., description="Whether the schedule is active")
    created_at: datetime = Field(..., description="When the schedule was created")
    
    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    """Response schema for list of schedules"""
    schedules: list[ScheduleResponse] = Field(..., description="List of schedules")
    total: int = Field(..., description="Total number of schedules")


class ScheduleDeleteResponse(BaseModel):
    """Response schema for schedule deletion"""
    success: bool = Field(..., description="Whether the deletion was successful")
    message: str = Field(..., description="Deletion result message")
