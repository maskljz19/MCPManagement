"""Pydantic schemas for AI Analysis service"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class FeasibilityReport(BaseModel):
    """Schema for AI feasibility analysis report"""
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Feasibility score from 0.0 (not feasible) to 1.0 (highly feasible)"
    )
    is_feasible: bool = Field(..., description="Whether the configuration is feasible")
    reasoning: str = Field(..., min_length=1, description="Explanation of the feasibility assessment")
    risks: List[str] = Field(default_factory=list, description="Identified risks")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improvement")
    
    @field_validator('reasoning')
    @classmethod
    def validate_reasoning_not_empty(cls, v: str) -> str:
        """Ensure reasoning is not just whitespace"""
        if not v.strip():
            raise ValueError('Reasoning cannot be empty or whitespace only')
        return v


class Improvement(BaseModel):
    """Schema for a single improvement suggestion"""
    category: str = Field(..., description="Category of improvement (e.g., performance, security)")
    title: str = Field(..., min_length=1, max_length=200, description="Brief title of the improvement")
    description: str = Field(..., min_length=1, description="Detailed description of the improvement")
    priority: str = Field(
        ...,
        pattern=r'^(low|medium|high|critical)$',
        description="Priority level"
    )
    effort: str = Field(
        ...,
        pattern=r'^(low|medium|high)$',
        description="Estimated effort to implement"
    )
    impact: str = Field(
        ...,
        pattern=r'^(low|medium|high)$',
        description="Expected impact of the improvement"
    )


class ConfigRequirements(BaseModel):
    """Schema for configuration generation requirements"""
    tool_name: str = Field(..., min_length=1, max_length=255, description="Name of the tool")
    description: str = Field(..., min_length=1, description="Description of what the tool should do")
    capabilities: List[str] = Field(
        ...,
        min_length=1,
        description="List of required capabilities"
    )
    constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="Constraints and limitations"
    )
    
    @field_validator('capabilities')
    @classmethod
    def validate_capabilities_not_empty(cls, v: List[str]) -> List[str]:
        """Ensure capabilities list is not empty and contains valid entries"""
        if not v:
            raise ValueError('At least one capability must be specified')
        if any(not cap.strip() for cap in v):
            raise ValueError('Capabilities cannot be empty or whitespace only')
        return v


class AnalysisRequest(BaseModel):
    """Schema for AI analysis request"""
    tool_id: Optional[UUID] = Field(None, description="ID of existing tool to analyze")
    config: Optional[Dict[str, Any]] = Field(None, description="Configuration to analyze")
    analysis_type: str = Field(
        ...,
        pattern=r'^(feasibility|improvements|generate_config)$',
        description="Type of analysis to perform"
    )
    requirements: Optional[ConfigRequirements] = Field(
        None,
        description="Requirements for config generation (required if analysis_type is generate_config)"
    )
    
    @field_validator('requirements')
    @classmethod
    def validate_requirements_for_generation(cls, v: Optional[ConfigRequirements], info) -> Optional[ConfigRequirements]:
        """Ensure requirements are provided for config generation"""
        if 'analysis_type' in info.data and info.data['analysis_type'] == 'generate_config':
            if v is None:
                raise ValueError('Requirements must be provided for config generation')
        return v
