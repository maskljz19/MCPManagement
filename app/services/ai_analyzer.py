"""AI Analyzer Service using LangChain and OpenAI"""

from typing import List, Dict, Any, Optional
from uuid import UUID
import json
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from motor.motor_asyncio import AsyncIOMotorClient

from app.schemas.ai_analysis import (
    FeasibilityReport,
    Improvement,
    ConfigRequirements
)
from app.core.config import settings


class AIAnalyzer:
    """
    AI Analyzer component for MCP tool analysis.
    
    Provides:
    - Feasibility analysis of MCP configurations
    - Improvement suggestions generation
    - Auto-configuration generation
    """
    
    def __init__(
        self,
        mongo_client: AsyncIOMotorClient,
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize AI Analyzer with LangChain and OpenAI.
        
        Args:
            mongo_client: MongoDB client for result persistence
            openai_api_key: OpenAI API key (defaults to settings)
        """
        self.mongo_client = mongo_client
        self.db = mongo_client[settings.MONGODB_DATABASE]
        self.results_collection = self.db["task_results"]
        
        # Initialize LangChain ChatOpenAI
        api_key = openai_api_key or settings.OPENAI_API_KEY
        base_url = settings.OPENAI_API_BASE or "https://api.openai.com/v1"
        if not api_key:
            raise ValueError("OpenAI API key is required for AI Analyzer")
        
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.2,
            api_key=api_key,
            base_url=base_url
        )
        
        # Initialize output parsers
        self.feasibility_parser = PydanticOutputParser(
            pydantic_object=FeasibilityReport
        )
        
        # Create prompt templates
        self._setup_prompts()
    
    def _setup_prompts(self):
        """Set up prompt templates for different analysis tasks"""
        
        # Feasibility analysis prompt
        self.feasibility_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in Model Context Protocol (MCP) tools and configurations.
Analyze the provided MCP configuration for feasibility and provide a detailed assessment.

{format_instructions}"""),
            ("user", """Analyze the following MCP tool configuration for feasibility:

Configuration:
{config}

Provide a comprehensive feasibility analysis including:
1. A feasibility score (0.0 to 1.0)
2. Whether the configuration is feasible (true/false)
3. Detailed reasoning for your assessment
4. Identified risks and concerns
5. Recommendations for improvement""")
        ])
        
        # Improvement suggestions prompt
        self.improvements_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in Model Context Protocol (MCP) tools and best practices.
Analyze the provided MCP tool and suggest concrete improvements.

Provide your response as a JSON array of improvement objects, where each object has:
- category: string (e.g., "performance", "security", "usability")
- title: string (brief title)
- description: string (detailed description)
- priority: string ("low", "medium", "high", or "critical")
- effort: string ("low", "medium", or "high")
- impact: string ("low", "medium", or "high")

Example:
[
  {{
    "category": "security",
    "title": "Add API key validation",
    "description": "Implement proper API key validation to prevent unauthorized access",
    "priority": "high",
    "effort": "medium",
    "impact": "high"
  }}
]"""),
            ("user", """Analyze the following MCP tool and suggest improvements:

Tool Name: {tool_name}
Description: {description}
Configuration:
{config}

Provide at least 3 actionable improvement suggestions.""")
        ])
        
        # Configuration generation prompt
        self.config_generation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in Model Context Protocol (MCP) tool configuration.
Generate a valid MCP configuration based on the provided requirements.

The configuration should be a valid JSON object following the MCP specification with:
- servers: array of server configurations
- tools: array of tool definitions
- prompts: array of prompt templates (optional)

Ensure the configuration is complete, valid, and follows best practices."""),
            ("user", """Generate an MCP configuration for the following requirements:

Tool Name: {tool_name}
Description: {description}
Required Capabilities: {capabilities}
Constraints: {constraints}

Provide a complete, valid MCP configuration as a JSON object.""")
        ])
    
    async def analyze_feasibility(
        self,
        config: Dict[str, Any],
        tool_name: Optional[str] = None
    ) -> FeasibilityReport:
        """
        Analyze the feasibility of an MCP configuration.
        
        Args:
            config: MCP configuration to analyze
            tool_name: Optional tool name for context
        
        Returns:
            FeasibilityReport with score, reasoning, risks, and recommendations
        
        Validates: Requirements 3.1
        """
        try:
            # Format the prompt
            format_instructions = self.feasibility_parser.get_format_instructions()
            prompt = self.feasibility_prompt.format_messages(
                config=json.dumps(config, indent=2),
                format_instructions=format_instructions
            )
            
            # Invoke LLM
            response = await self.llm.ainvoke(prompt)
            
            # Parse response
            report = self.feasibility_parser.parse(response.content)
            
            return report
            
        except Exception as e:
            # Log the error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"OpenAI API error in feasibility analysis: {str(e)}", exc_info=True)
            
            # Determine error type and provide helpful message
            error_msg = str(e).lower()
            if "api key" in error_msg or "authentication" in error_msg:
                error_detail = "OpenAI API 密钥无效或未配置。请在环境变量中设置有效的 OPENAI_API_KEY。"
            elif "rate limit" in error_msg:
                error_detail = "OpenAI API 速率限制已达到。请稍后重试或升级您的 OpenAI 账户。"
            elif "timeout" in error_msg or "connection" in error_msg:
                error_detail = "无法连接到 OpenAI API。请检查网络连接、防火墙设置或 OPENAI_API_BASE 配置。"
            elif "model" in error_msg:
                error_detail = "指定的 AI 模型不可用。请检查您的 OpenAI 账户权限。"
            else:
                error_detail = f"AI 分析服务暂时不可用: {str(e)}"
            
            # Re-raise with more context
            raise RuntimeError(f"Connection error. {error_detail}")
    
    async def suggest_improvements(
        self,
        tool_name: str,
        description: str,
        config: Dict[str, Any]
    ) -> List[Improvement]:
        """
        Generate improvement suggestions for an MCP tool.
        
        Args:
            tool_name: Name of the tool
            description: Tool description
            config: Current tool configuration
        
        Returns:
            List of Improvement suggestions
        
        Validates: Requirements 3.2
        """
        try:
            # Format the prompt
            prompt = self.improvements_prompt.format_messages(
                tool_name=tool_name,
                description=description or "No description provided",
                config=json.dumps(config, indent=2)
            )
            
            # Invoke LLM
            response = await self.llm.ainvoke(prompt)
            
            # Parse JSON response
            try:
                improvements_data = json.loads(response.content)
                improvements = [Improvement(**item) for item in improvements_data]
            except (json.JSONDecodeError, ValueError) as e:
                # Fallback: try to extract JSON from markdown code blocks
                content = response.content
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_str = content[json_start:json_end].strip()
                    improvements_data = json.loads(json_str)
                    improvements = [Improvement(**item) for item in improvements_data]
                else:
                    raise ValueError(f"Failed to parse improvements response: {e}")
            
            return improvements
            
        except Exception as e:
            # Log the error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"OpenAI API error in improvement suggestions: {str(e)}", exc_info=True)
            
            # Determine error type and provide helpful message
            error_msg = str(e).lower()
            if "api key" in error_msg or "authentication" in error_msg:
                error_detail = "OpenAI API 密钥无效或未配置。"
            elif "rate limit" in error_msg:
                error_detail = "OpenAI API 速率限制已达到。"
            elif "timeout" in error_msg or "connection" in error_msg:
                error_detail = "无法连接到 OpenAI API。"
            else:
                error_detail = f"AI 分析服务暂时不可用: {str(e)}"
            
            raise RuntimeError(f"Connection error. {error_detail}")
    
    async def generate_config(
        self,
        requirements: ConfigRequirements
    ) -> Dict[str, Any]:
        """
        Generate an MCP configuration based on requirements.
        
        Args:
            requirements: Configuration requirements
        
        Returns:
            Generated MCP configuration as dictionary
        
        Validates: Requirements 3.3
        """
        try:
            # Format the prompt
            prompt = self.config_generation_prompt.format_messages(
                tool_name=requirements.tool_name,
                description=requirements.description,
                capabilities=", ".join(requirements.capabilities),
                constraints=json.dumps(requirements.constraints, indent=2)
            )
            
            # Invoke LLM
            response = await self.llm.ainvoke(prompt)
            
            # Parse JSON response
            try:
                config = json.loads(response.content)
            except json.JSONDecodeError:
                # Fallback: try to extract JSON from markdown code blocks
                content = response.content
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_str = content[json_start:json_end].strip()
                    config = json.loads(json_str)
                else:
                    raise ValueError("Failed to parse generated configuration")
            
            return config
            
        except Exception as e:
            # Log the error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"OpenAI API error in config generation: {str(e)}", exc_info=True)
            
            # Determine error type and provide helpful message
            error_msg = str(e).lower()
            if "api key" in error_msg or "authentication" in error_msg:
                error_detail = "OpenAI API 密钥无效或未配置。"
            elif "rate limit" in error_msg:
                error_detail = "OpenAI API 速率限制已达到。"
            elif "timeout" in error_msg or "connection" in error_msg:
                error_detail = "无法连接到 OpenAI API。"
            else:
                error_detail = f"AI 分析服务暂时不可用: {str(e)}"
            
            raise RuntimeError(f"Connection error. {error_detail}")
    
    async def store_analysis_result(
        self,
        task_id: UUID,
        task_type: str,
        result: Any,
        ttl_hours: int = 24
    ) -> None:
        """
        Store analysis result in MongoDB with TTL.
        
        Args:
            task_id: Unique task identifier
            task_type: Type of analysis task
            result: Analysis result (will be serialized)
            ttl_hours: Time-to-live in hours (default 24)
        
        Validates: Requirements 3.5
        """
        # Calculate TTL expiration
        from datetime import timedelta, timezone
        ttl_expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
        
        # Serialize result
        if hasattr(result, 'model_dump'):
            result_data = result.model_dump()
        elif isinstance(result, list) and all(hasattr(item, 'model_dump') for item in result):
            result_data = [item.model_dump() for item in result]
        elif isinstance(result, dict):
            result_data = result
        else:
            result_data = {"value": str(result)}
        
        # Store in MongoDB
        document = {
            "task_id": str(task_id),
            "task_type": task_type,
            "status": "completed",
            "result": result_data,
            "created_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc),
            "ttl_expires_at": ttl_expires_at
        }
        
        await self.results_collection.insert_one(document)
    
    async def get_analysis_result(
        self,
        task_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve analysis result from MongoDB.
        
        Args:
            task_id: Task identifier
        
        Returns:
            Analysis result document or None if not found
        """
        result = await self.results_collection.find_one(
            {"task_id": str(task_id)}
        )
        
        if result:
            # Remove MongoDB _id field
            result.pop('_id', None)
        
        return result
    
    async def ensure_ttl_index(self):
        """
        Ensure TTL index exists on task_results collection.
        
        This should be called during application startup.
        """
        await self.results_collection.create_index(
            "ttl_expires_at",
            expireAfterSeconds=0
        )
