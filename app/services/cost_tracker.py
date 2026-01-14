"""
Cost Tracker Service - Calculates and tracks execution costs.

This service is responsible for:
- Calculating execution costs based on duration and resource usage
- Storing cost data with execution records
- Aggregating costs by user, tool, and time period
- Checking cost thresholds and sending notifications
- Generating cost reports

Requirements: 18.1, 18.2, 18.3, 18.4, 18.5
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from decimal import Decimal
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.sql import Select

from app.models.execution_cost import ExecutionCostModel
from app.models.user import UserModel
from app.models.mcp_tool import MCPToolModel


logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class ToolPricing:
    """Pricing configuration for a tool"""
    tool_id: UUID
    base_cost_per_execution: Decimal = Decimal("0.01")
    cost_per_second: Decimal = Decimal("0.001")
    cost_per_cpu_second: Decimal = Decimal("0.0001")
    cost_per_mb_second: Decimal = Decimal("0.00001")
    currency: str = "USD"


@dataclass
class ExecutionCost:
    """Calculated cost for an execution"""
    execution_id: UUID
    user_id: UUID
    tool_id: UUID
    cost_amount: Decimal
    currency: str
    duration_seconds: float
    cpu_cores: float
    memory_mb: int
    calculated_at: datetime


@dataclass
class DateRange:
    """Date range for queries"""
    start_date: datetime
    end_date: datetime


@dataclass
class CostSummary:
    """Summary of costs for a user"""
    user_id: UUID
    total_cost: Decimal
    currency: str
    execution_count: int
    period_start: datetime
    period_end: datetime
    costs_by_tool: Dict[str, Decimal]
    costs_by_day: Dict[str, Decimal]


@dataclass
class CostFilters:
    """Filters for cost queries"""
    user_id: Optional[UUID] = None
    tool_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_cost: Optional[Decimal] = None
    max_cost: Optional[Decimal] = None


@dataclass
class CostReport:
    """Detailed cost report"""
    total_cost: Decimal
    currency: str
    execution_count: int
    period_start: datetime
    period_end: datetime
    costs_by_user: Dict[str, Decimal]
    costs_by_tool: Dict[str, Decimal]
    costs_by_day: Dict[str, Decimal]
    top_users: List[Dict[str, Any]]
    top_tools: List[Dict[str, Any]]


@dataclass
class CostThreshold:
    """Cost threshold configuration"""
    user_id: UUID
    daily_limit: Optional[Decimal] = None
    monthly_limit: Optional[Decimal] = None
    notification_thresholds: List[float] = None  # e.g., [0.5, 0.75, 0.9, 1.0]
    block_on_exceed: bool = False


@dataclass
class ThresholdStatus:
    """Status of cost threshold"""
    user_id: UUID
    current_daily_cost: Decimal
    current_monthly_cost: Decimal
    daily_limit: Optional[Decimal]
    monthly_limit: Optional[Decimal]
    daily_percentage: Optional[float]
    monthly_percentage: Optional[float]
    daily_exceeded: bool
    monthly_exceeded: bool
    notifications_triggered: List[str]


# ============================================================================
# Cost Tracker
# ============================================================================


class CostTracker:
    """
    Tracks and manages execution costs.
    
    Calculates costs based on resource usage and provides cost reporting
    and threshold management.
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        default_pricing: Optional[ToolPricing] = None
    ):
        """
        Initialize the cost tracker.
        
        Args:
            db_session: Database session for cost storage
            default_pricing: Default pricing configuration
        """
        self.db = db_session
        self.default_pricing = default_pricing or ToolPricing(
            tool_id=UUID("00000000-0000-0000-0000-000000000000"),
            base_cost_per_execution=Decimal("0.01"),
            cost_per_second=Decimal("0.001"),
            cost_per_cpu_second=Decimal("0.0001"),
            cost_per_mb_second=Decimal("0.00001"),
            currency="USD"
        )
        
        # In-memory cache for tool pricing (would be loaded from config/database)
        self.tool_pricing_cache: Dict[UUID, ToolPricing] = {}
        
        # In-memory cache for cost thresholds (would be loaded from database)
        self.threshold_cache: Dict[UUID, CostThreshold] = {}
    
    def _get_tool_pricing(self, tool_id: UUID) -> ToolPricing:
        """
        Get pricing configuration for a tool.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            Tool pricing configuration
        """
        # Check cache first
        if tool_id in self.tool_pricing_cache:
            return self.tool_pricing_cache[tool_id]
        
        # TODO: Load from database or configuration
        # For now, return default pricing
        return self.default_pricing
    
    async def calculate_cost(
        self,
        execution_id: UUID,
        user_id: UUID,
        tool_id: UUID,
        duration_seconds: float,
        cpu_cores: float,
        memory_mb: int
    ) -> ExecutionCost:
        """
        Calculate cost for an execution.
        
        Args:
            execution_id: Execution identifier
            user_id: User identifier
            tool_id: Tool identifier
            duration_seconds: Execution duration in seconds
            cpu_cores: CPU cores used
            memory_mb: Memory used in MB
            
        Returns:
            Calculated execution cost
            
        Requirements: 18.1
        """
        try:
            # Get pricing for the tool
            pricing = self._get_tool_pricing(tool_id)
            
            # Calculate cost components
            base_cost = pricing.base_cost_per_execution
            duration_cost = Decimal(str(duration_seconds)) * pricing.cost_per_second
            cpu_cost = Decimal(str(cpu_cores)) * Decimal(str(duration_seconds)) * pricing.cost_per_cpu_second
            memory_cost = Decimal(str(memory_mb)) * Decimal(str(duration_seconds)) * pricing.cost_per_mb_second
            
            # Total cost
            total_cost = base_cost + duration_cost + cpu_cost + memory_cost
            
            # Round to 4 decimal places
            total_cost = total_cost.quantize(Decimal("0.0001"))
            
            execution_cost = ExecutionCost(
                execution_id=execution_id,
                user_id=user_id,
                tool_id=tool_id,
                cost_amount=total_cost,
                currency=pricing.currency,
                duration_seconds=duration_seconds,
                cpu_cores=cpu_cores,
                memory_mb=memory_mb,
                calculated_at=datetime.utcnow()
            )
            
            logger.info(
                f"Calculated cost for execution {execution_id}: "
                f"{total_cost} {pricing.currency} "
                f"(duration={duration_seconds}s, cpu={cpu_cores}, memory={memory_mb}MB)"
            )
            
            return execution_cost
        
        except Exception as e:
            logger.error(f"Failed to calculate cost: {e}")
            raise
    
    async def store_cost(self, cost: ExecutionCost) -> ExecutionCostModel:
        """
        Store execution cost in the database.
        
        Args:
            cost: Execution cost to store
            
        Returns:
            Stored cost model
            
        Requirements: 18.2
        """
        try:
            cost_model = ExecutionCostModel(
                execution_id=str(cost.execution_id),
                user_id=str(cost.user_id),
                tool_id=str(cost.tool_id),
                cost_amount=cost.cost_amount,
                currency=cost.currency,
                duration_seconds=cost.duration_seconds,
                cpu_cores=cost.cpu_cores,
                memory_mb=cost.memory_mb,
                calculated_at=cost.calculated_at
            )
            
            self.db.add(cost_model)
            await self.db.commit()
            await self.db.refresh(cost_model)
            
            logger.info(
                f"Stored cost for execution {cost.execution_id}: "
                f"{cost.cost_amount} {cost.currency}"
            )
            
            return cost_model
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to store cost: {e}")
            raise
    
    async def get_user_costs(
        self,
        user_id: UUID,
        period: DateRange
    ) -> CostSummary:
        """
        Get cost summary for a user over a time period.
        
        Args:
            user_id: User identifier
            period: Date range for the query
            
        Returns:
            Cost summary for the user
            
        Requirements: 18.3
        """
        try:
            # Query total cost
            query = select(
                func.sum(ExecutionCostModel.cost_amount).label("total_cost"),
                func.count(ExecutionCostModel.id).label("execution_count"),
                ExecutionCostModel.currency
            ).where(
                and_(
                    ExecutionCostModel.user_id == str(user_id),
                    ExecutionCostModel.calculated_at >= period.start_date,
                    ExecutionCostModel.calculated_at <= period.end_date
                )
            ).group_by(ExecutionCostModel.currency)
            
            result = await self.db.execute(query)
            row = result.first()
            
            if not row or row.total_cost is None:
                return CostSummary(
                    user_id=user_id,
                    total_cost=Decimal("0.0000"),
                    currency="USD",
                    execution_count=0,
                    period_start=period.start_date,
                    period_end=period.end_date,
                    costs_by_tool={},
                    costs_by_day={}
                )
            
            total_cost = Decimal(str(row.total_cost))
            execution_count = row.execution_count
            currency = row.currency
            
            # Query costs by tool
            tool_query = select(
                ExecutionCostModel.tool_id,
                func.sum(ExecutionCostModel.cost_amount).label("tool_cost")
            ).where(
                and_(
                    ExecutionCostModel.user_id == str(user_id),
                    ExecutionCostModel.calculated_at >= period.start_date,
                    ExecutionCostModel.calculated_at <= period.end_date
                )
            ).group_by(ExecutionCostModel.tool_id)
            
            tool_result = await self.db.execute(tool_query)
            costs_by_tool = {
                row.tool_id: Decimal(str(row.tool_cost))
                for row in tool_result.fetchall()
            }
            
            # Query costs by day
            day_query = select(
                func.date(ExecutionCostModel.calculated_at).label("day"),
                func.sum(ExecutionCostModel.cost_amount).label("day_cost")
            ).where(
                and_(
                    ExecutionCostModel.user_id == str(user_id),
                    ExecutionCostModel.calculated_at >= period.start_date,
                    ExecutionCostModel.calculated_at <= period.end_date
                )
            ).group_by(func.date(ExecutionCostModel.calculated_at))
            
            day_result = await self.db.execute(day_query)
            costs_by_day = {
                str(row.day): Decimal(str(row.day_cost))
                for row in day_result.fetchall()
            }
            
            summary = CostSummary(
                user_id=user_id,
                total_cost=total_cost,
                currency=currency,
                execution_count=execution_count,
                period_start=period.start_date,
                period_end=period.end_date,
                costs_by_tool=costs_by_tool,
                costs_by_day=costs_by_day
            )
            
            logger.info(
                f"Retrieved cost summary for user {user_id}: "
                f"{total_cost} {currency} ({execution_count} executions)"
            )
            
            return summary
        
        except Exception as e:
            logger.error(f"Failed to get user costs: {e}")
            raise

    async def check_cost_threshold(
        self,
        user_id: UUID
    ) -> ThresholdStatus:
        """
        Check if user has exceeded cost thresholds.
        
        Args:
            user_id: User identifier
            
        Returns:
            Threshold status with notifications
            
        Requirements: 18.4
        """
        try:
            # Get threshold configuration for user
            threshold = self.threshold_cache.get(user_id)
            
            if not threshold:
                # No threshold configured, return default status
                return ThresholdStatus(
                    user_id=user_id,
                    current_daily_cost=Decimal("0.0000"),
                    current_monthly_cost=Decimal("0.0000"),
                    daily_limit=None,
                    monthly_limit=None,
                    daily_percentage=None,
                    monthly_percentage=None,
                    daily_exceeded=False,
                    monthly_exceeded=False,
                    notifications_triggered=[]
                )
            
            # Get current daily cost
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.utcnow()
            daily_period = DateRange(start_date=today_start, end_date=today_end)
            daily_summary = await self.get_user_costs(user_id, daily_period)
            
            # Get current monthly cost
            month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = datetime.utcnow()
            monthly_period = DateRange(start_date=month_start, end_date=month_end)
            monthly_summary = await self.get_user_costs(user_id, monthly_period)
            
            # Calculate percentages
            daily_percentage = None
            monthly_percentage = None
            
            if threshold.daily_limit and threshold.daily_limit > 0:
                daily_percentage = float(daily_summary.total_cost / threshold.daily_limit)
            
            if threshold.monthly_limit and threshold.monthly_limit > 0:
                monthly_percentage = float(monthly_summary.total_cost / threshold.monthly_limit)
            
            # Check if exceeded
            daily_exceeded = (
                threshold.daily_limit is not None and
                daily_summary.total_cost >= threshold.daily_limit
            )
            
            monthly_exceeded = (
                threshold.monthly_limit is not None and
                monthly_summary.total_cost >= threshold.monthly_limit
            )
            
            # Determine which notifications should be triggered
            notifications_triggered = []
            
            if threshold.notification_thresholds:
                for threshold_pct in threshold.notification_thresholds:
                    if daily_percentage and daily_percentage >= threshold_pct:
                        notifications_triggered.append(f"daily_{int(threshold_pct * 100)}%")
                    if monthly_percentage and monthly_percentage >= threshold_pct:
                        notifications_triggered.append(f"monthly_{int(threshold_pct * 100)}%")
            
            status = ThresholdStatus(
                user_id=user_id,
                current_daily_cost=daily_summary.total_cost,
                current_monthly_cost=monthly_summary.total_cost,
                daily_limit=threshold.daily_limit,
                monthly_limit=threshold.monthly_limit,
                daily_percentage=daily_percentage,
                monthly_percentage=monthly_percentage,
                daily_exceeded=daily_exceeded,
                monthly_exceeded=monthly_exceeded,
                notifications_triggered=notifications_triggered
            )
            
            # Send notifications if thresholds exceeded
            if notifications_triggered:
                await self._send_threshold_notifications(user_id, status)
            
            # Block executions if configured and exceeded
            if threshold.block_on_exceed and (daily_exceeded or monthly_exceeded):
                logger.warning(
                    f"User {user_id} has exceeded cost threshold. "
                    f"Daily: {daily_summary.total_cost}/{threshold.daily_limit}, "
                    f"Monthly: {monthly_summary.total_cost}/{threshold.monthly_limit}"
                )
            
            return status
        
        except Exception as e:
            logger.error(f"Failed to check cost threshold: {e}")
            raise
    
    async def _send_threshold_notifications(
        self,
        user_id: UUID,
        status: ThresholdStatus
    ) -> None:
        """
        Send notifications for threshold breaches.
        
        Args:
            user_id: User identifier
            status: Threshold status
        """
        try:
            # Log notification
            logger.warning(
                f"Cost threshold notification for user {user_id}: "
                f"Daily: {status.current_daily_cost}/{status.daily_limit} "
                f"({status.daily_percentage:.1%} if status.daily_percentage else 'N/A'), "
                f"Monthly: {status.current_monthly_cost}/{status.monthly_limit} "
                f"({status.monthly_percentage:.1%} if status.monthly_percentage else 'N/A')"
            )
            
            # TODO: Integrate with notification system (email, Slack, etc.)
            # This would be implemented based on the organization's notification infrastructure
            
        except Exception as e:
            logger.error(f"Failed to send threshold notifications: {e}")
    
    async def generate_cost_report(
        self,
        filters: CostFilters
    ) -> CostReport:
        """
        Generate a detailed cost report.
        
        Args:
            filters: Filters for the report
            
        Returns:
            Detailed cost report
            
        Requirements: 18.5
        """
        try:
            # Build base query
            query_conditions = []
            
            if filters.user_id:
                query_conditions.append(ExecutionCostModel.user_id == str(filters.user_id))
            
            if filters.tool_id:
                query_conditions.append(ExecutionCostModel.tool_id == str(filters.tool_id))
            
            if filters.start_date:
                query_conditions.append(ExecutionCostModel.calculated_at >= filters.start_date)
            
            if filters.end_date:
                query_conditions.append(ExecutionCostModel.calculated_at <= filters.end_date)
            
            if filters.min_cost:
                query_conditions.append(ExecutionCostModel.cost_amount >= filters.min_cost)
            
            if filters.max_cost:
                query_conditions.append(ExecutionCostModel.cost_amount <= filters.max_cost)
            
            # Query total cost and execution count
            total_query = select(
                func.sum(ExecutionCostModel.cost_amount).label("total_cost"),
                func.count(ExecutionCostModel.id).label("execution_count"),
                ExecutionCostModel.currency
            )
            
            if query_conditions:
                total_query = total_query.where(and_(*query_conditions))
            
            total_query = total_query.group_by(ExecutionCostModel.currency)
            
            total_result = await self.db.execute(total_query)
            total_row = total_result.first()
            
            if not total_row or total_row.total_cost is None:
                # Return empty report
                return CostReport(
                    total_cost=Decimal("0.0000"),
                    currency="USD",
                    execution_count=0,
                    period_start=filters.start_date or datetime.utcnow(),
                    period_end=filters.end_date or datetime.utcnow(),
                    costs_by_user={},
                    costs_by_tool={},
                    costs_by_day={},
                    top_users=[],
                    top_tools=[]
                )
            
            total_cost = Decimal(str(total_row.total_cost))
            execution_count = total_row.execution_count
            currency = total_row.currency
            
            # Query costs by user
            user_query = select(
                ExecutionCostModel.user_id,
                func.sum(ExecutionCostModel.cost_amount).label("user_cost")
            )
            
            if query_conditions:
                user_query = user_query.where(and_(*query_conditions))
            
            user_query = user_query.group_by(ExecutionCostModel.user_id)
            
            user_result = await self.db.execute(user_query)
            costs_by_user = {
                row.user_id: Decimal(str(row.user_cost))
                for row in user_result.fetchall()
            }
            
            # Query costs by tool
            tool_query = select(
                ExecutionCostModel.tool_id,
                func.sum(ExecutionCostModel.cost_amount).label("tool_cost")
            )
            
            if query_conditions:
                tool_query = tool_query.where(and_(*query_conditions))
            
            tool_query = tool_query.group_by(ExecutionCostModel.tool_id)
            
            tool_result = await self.db.execute(tool_query)
            costs_by_tool = {
                row.tool_id: Decimal(str(row.tool_cost))
                for row in tool_result.fetchall()
            }
            
            # Query costs by day
            day_query = select(
                func.date(ExecutionCostModel.calculated_at).label("day"),
                func.sum(ExecutionCostModel.cost_amount).label("day_cost")
            )
            
            if query_conditions:
                day_query = day_query.where(and_(*query_conditions))
            
            day_query = day_query.group_by(func.date(ExecutionCostModel.calculated_at))
            
            day_result = await self.db.execute(day_query)
            costs_by_day = {
                str(row.day): Decimal(str(row.day_cost))
                for row in day_result.fetchall()
            }
            
            # Get top users
            top_users_query = select(
                ExecutionCostModel.user_id,
                func.sum(ExecutionCostModel.cost_amount).label("total_cost"),
                func.count(ExecutionCostModel.id).label("execution_count")
            )
            
            if query_conditions:
                top_users_query = top_users_query.where(and_(*query_conditions))
            
            top_users_query = (
                top_users_query
                .group_by(ExecutionCostModel.user_id)
                .order_by(func.sum(ExecutionCostModel.cost_amount).desc())
                .limit(10)
            )
            
            top_users_result = await self.db.execute(top_users_query)
            top_users = [
                {
                    "user_id": row.user_id,
                    "total_cost": Decimal(str(row.total_cost)),
                    "execution_count": row.execution_count
                }
                for row in top_users_result.fetchall()
            ]
            
            # Get top tools
            top_tools_query = select(
                ExecutionCostModel.tool_id,
                func.sum(ExecutionCostModel.cost_amount).label("total_cost"),
                func.count(ExecutionCostModel.id).label("execution_count")
            )
            
            if query_conditions:
                top_tools_query = top_tools_query.where(and_(*query_conditions))
            
            top_tools_query = (
                top_tools_query
                .group_by(ExecutionCostModel.tool_id)
                .order_by(func.sum(ExecutionCostModel.cost_amount).desc())
                .limit(10)
            )
            
            top_tools_result = await self.db.execute(top_tools_query)
            top_tools = [
                {
                    "tool_id": row.tool_id,
                    "total_cost": Decimal(str(row.total_cost)),
                    "execution_count": row.execution_count
                }
                for row in top_tools_result.fetchall()
            ]
            
            report = CostReport(
                total_cost=total_cost,
                currency=currency,
                execution_count=execution_count,
                period_start=filters.start_date or datetime.utcnow(),
                period_end=filters.end_date or datetime.utcnow(),
                costs_by_user=costs_by_user,
                costs_by_tool=costs_by_tool,
                costs_by_day=costs_by_day,
                top_users=top_users,
                top_tools=top_tools
            )
            
            logger.info(
                f"Generated cost report: {total_cost} {currency} "
                f"({execution_count} executions)"
            )
            
            return report
        
        except Exception as e:
            logger.error(f"Failed to generate cost report: {e}")
            raise
    
    def set_cost_threshold(
        self,
        user_id: UUID,
        threshold: CostThreshold
    ) -> None:
        """
        Set cost threshold for a user.
        
        Args:
            user_id: User identifier
            threshold: Threshold configuration
        """
        self.threshold_cache[user_id] = threshold
        logger.info(
            f"Set cost threshold for user {user_id}: "
            f"daily={threshold.daily_limit}, monthly={threshold.monthly_limit}"
        )
    
    def get_cost_threshold(self, user_id: UUID) -> Optional[CostThreshold]:
        """
        Get cost threshold for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Threshold configuration or None
        """
        return self.threshold_cache.get(user_id)
    
    def set_tool_pricing(self, tool_id: UUID, pricing: ToolPricing) -> None:
        """
        Set pricing configuration for a tool.
        
        Args:
            tool_id: Tool identifier
            pricing: Pricing configuration
        """
        self.tool_pricing_cache[tool_id] = pricing
        logger.info(
            f"Set pricing for tool {tool_id}: "
            f"base={pricing.base_cost_per_execution}, "
            f"per_second={pricing.cost_per_second}"
        )
    
    def get_tool_pricing(self, tool_id: UUID) -> ToolPricing:
        """
        Get pricing configuration for a tool.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            Pricing configuration
        """
        return self._get_tool_pricing(tool_id)


# ============================================================================
# Helper Functions
# ============================================================================


def create_cost_tracker(
    db_session: AsyncSession,
    default_pricing: Optional[ToolPricing] = None
) -> CostTracker:
    """
    Factory function to create a CostTracker instance.
    
    Args:
        db_session: Database session
        default_pricing: Default pricing configuration
        
    Returns:
        CostTracker instance
    """
    return CostTracker(
        db_session=db_session,
        default_pricing=default_pricing
    )
