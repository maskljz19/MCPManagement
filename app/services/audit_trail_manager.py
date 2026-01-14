"""
Audit Trail Manager Service - Records and manages execution audit trails.

This service is responsible for:
- Recording audit events for execution lifecycle
- Querying audit trails with filtering
- Exporting audit trails in tamper-evident format
- Storing audit events in MongoDB

Requirements: 17.1, 17.2, 17.3, 17.4, 17.5
"""

import logging
import hashlib
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID
from dataclasses import dataclass, asdict
from enum import Enum

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING


logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


class AuditEventType(str, Enum):
    """Types of audit events"""
    EXECUTION_INITIATED = "execution_initiated"
    EXECUTION_QUEUED = "execution_queued"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_STATUS_CHANGED = "execution_status_changed"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_CANCELLED = "execution_cancelled"
    EXECUTION_TIMEOUT = "execution_timeout"
    EXECUTION_RETRY = "execution_retry"


@dataclass
class ResourceUsage:
    """Resource usage information"""
    cpu_cores_used: float
    memory_mb_used: int
    duration_ms: int


@dataclass
class AuditEvent:
    """Audit event for execution tracking"""
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    user_id: UUID
    tool_id: UUID
    execution_id: UUID
    parameters: Dict[str, Any]
    result_summary: Optional[str] = None
    status: Optional[str] = None
    duration_ms: Optional[int] = None
    resource_usage: Optional[ResourceUsage] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AuditFilters:
    """Filters for querying audit trail"""
    user_id: Optional[UUID] = None
    tool_id: Optional[UUID] = None
    execution_id: Optional[UUID] = None
    event_type: Optional[AuditEventType] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100
    skip: int = 0


# ============================================================================
# Audit Trail Manager
# ============================================================================


class AuditTrailManager:
    """
    Manages audit trails for MCP tool executions.
    
    Records comprehensive audit logs for compliance and tracking purposes.
    """
    
    def __init__(self, mongo_db: AsyncIOMotorDatabase):
        """
        Initialize the audit trail manager.
        
        Args:
            mongo_db: MongoDB database for audit storage
        """
        self.mongo = mongo_db
        self.audit_collection = mongo_db["mcp_audit_trail"]
        
        # Initialize indexes
        self._initialized = False
    
    async def _ensure_indexes(self) -> None:
        """Create indexes for efficient querying"""
        if self._initialized:
            return
        
        try:
            # Create indexes for common query patterns
            await self.audit_collection.create_index([("timestamp", DESCENDING)])
            await self.audit_collection.create_index([("user_id", ASCENDING)])
            await self.audit_collection.create_index([("tool_id", ASCENDING)])
            await self.audit_collection.create_index([("execution_id", ASCENDING)])
            await self.audit_collection.create_index([("event_type", ASCENDING)])
            await self.audit_collection.create_index([("status", ASCENDING)])
            
            # Compound indexes for common filter combinations
            await self.audit_collection.create_index([
                ("user_id", ASCENDING),
                ("timestamp", DESCENDING)
            ])
            await self.audit_collection.create_index([
                ("tool_id", ASCENDING),
                ("timestamp", DESCENDING)
            ])
            await self.audit_collection.create_index([
                ("execution_id", ASCENDING),
                ("timestamp", ASCENDING)
            ])
            
            self._initialized = True
            logger.info("Audit trail indexes created successfully")
        
        except Exception as e:
            logger.error(f"Failed to create audit trail indexes: {e}")
    
    async def log_execution_event(self, event: AuditEvent) -> None:
        """
        Log an audit event for an execution.
        
        Args:
            event: Audit event to log
            
        Requirement: 17.1, 17.2, 17.3
        """
        try:
            # Ensure indexes are created
            await self._ensure_indexes()
            
            # Convert event to dictionary
            event_dict = self._event_to_dict(event)
            
            # Insert into MongoDB
            await self.audit_collection.insert_one(event_dict)
            
            logger.info(
                f"Logged audit event: {event.event_type.value} "
                f"(execution={event.execution_id}, user={event.user_id})"
            )
        
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            # Don't raise - audit logging should not break execution
    
    def _event_to_dict(self, event: AuditEvent) -> Dict[str, Any]:
        """
        Convert AuditEvent to dictionary for MongoDB storage.
        
        Args:
            event: Audit event
            
        Returns:
            Dictionary representation
        """
        event_dict = {
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "event_type": event.event_type.value,
            "user_id": str(event.user_id),
            "tool_id": str(event.tool_id),
            "execution_id": str(event.execution_id),
            "parameters": event.parameters,
        }
        
        # Add optional fields
        if event.result_summary is not None:
            event_dict["result_summary"] = event.result_summary
        
        if event.status is not None:
            event_dict["status"] = event.status
        
        if event.duration_ms is not None:
            event_dict["duration_ms"] = event.duration_ms
        
        if event.resource_usage is not None:
            event_dict["resource_usage"] = {
                "cpu_cores_used": event.resource_usage.cpu_cores_used,
                "memory_mb_used": event.resource_usage.memory_mb_used,
                "duration_ms": event.resource_usage.duration_ms
            }
        
        if event.ip_address is not None:
            event_dict["ip_address"] = event.ip_address
        
        if event.user_agent is not None:
            event_dict["user_agent"] = event.user_agent
        
        if event.error_message is not None:
            event_dict["error_message"] = event.error_message
        
        if event.metadata is not None:
            event_dict["metadata"] = event.metadata
        
        return event_dict
    
    async def query_audit_trail(
        self,
        filters: AuditFilters
    ) -> List[Dict[str, Any]]:
        """
        Query audit trail with filters.
        
        Args:
            filters: Filters for querying
            
        Returns:
            List of audit events matching filters
            
        Requirement: 17.4
        """
        try:
            # Ensure indexes are created
            await self._ensure_indexes()
            
            # Build query
            query = {}
            
            if filters.user_id:
                query["user_id"] = str(filters.user_id)
            
            if filters.tool_id:
                query["tool_id"] = str(filters.tool_id)
            
            if filters.execution_id:
                query["execution_id"] = str(filters.execution_id)
            
            if filters.event_type:
                query["event_type"] = filters.event_type.value
            
            if filters.status:
                query["status"] = filters.status
            
            # Date range filter
            if filters.start_date or filters.end_date:
                date_filter = {}
                if filters.start_date:
                    date_filter["$gte"] = filters.start_date
                if filters.end_date:
                    date_filter["$lte"] = filters.end_date
                query["timestamp"] = date_filter
            
            # Execute query with pagination
            cursor = self.audit_collection.find(query).sort(
                "timestamp", DESCENDING
            ).skip(filters.skip).limit(filters.limit)
            
            results = await cursor.to_list(length=filters.limit)
            
            logger.info(
                f"Queried audit trail: {len(results)} events found "
                f"(filters={filters})"
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Failed to query audit trail: {e}")
            raise
    
    async def export_audit_trail(
        self,
        filters: AuditFilters,
        format: str = "json"
    ) -> bytes:
        """
        Export audit trail in tamper-evident format.
        
        Args:
            filters: Filters for export
            format: Export format ("json" or "csv")
            
        Returns:
            Exported data as bytes
            
        Requirement: 17.5
        """
        try:
            # Query all matching events (no pagination for export)
            export_filters = AuditFilters(
                user_id=filters.user_id,
                tool_id=filters.tool_id,
                execution_id=filters.execution_id,
                event_type=filters.event_type,
                status=filters.status,
                start_date=filters.start_date,
                end_date=filters.end_date,
                limit=10000,  # Large limit for export
                skip=0
            )
            
            events = await self.query_audit_trail(export_filters)
            
            if format == "json":
                return self._export_json(events)
            elif format == "csv":
                return self._export_csv(events)
            else:
                raise ValueError(f"Unsupported export format: {format}")
        
        except Exception as e:
            logger.error(f"Failed to export audit trail: {e}")
            raise
    
    def _export_json(self, events: List[Dict[str, Any]]) -> bytes:
        """
        Export events as JSON with tamper-evident checksum.
        
        Args:
            events: List of audit events
            
        Returns:
            JSON bytes with checksum
        """
        # Convert ObjectId and datetime to strings for JSON serialization
        serializable_events = []
        for event in events:
            serializable_event = {}
            for key, value in event.items():
                if key == "_id":
                    continue  # Skip MongoDB internal ID
                elif isinstance(value, datetime):
                    serializable_event[key] = value.isoformat()
                else:
                    serializable_event[key] = value
            serializable_events.append(serializable_event)
        
        # Create export data
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "event_count": len(serializable_events),
            "events": serializable_events
        }
        
        # Calculate checksum for tamper detection
        events_json = json.dumps(serializable_events, sort_keys=True)
        checksum = hashlib.sha256(events_json.encode()).hexdigest()
        export_data["checksum"] = checksum
        export_data["checksum_algorithm"] = "SHA-256"
        
        # Serialize to JSON
        json_bytes = json.dumps(export_data, indent=2).encode('utf-8')
        
        logger.info(
            f"Exported {len(events)} audit events as JSON "
            f"(checksum={checksum[:16]}...)"
        )
        
        return json_bytes
    
    def _export_csv(self, events: List[Dict[str, Any]]) -> bytes:
        """
        Export events as CSV with tamper-evident checksum.
        
        Args:
            events: List of audit events
            
        Returns:
            CSV bytes with checksum header
        """
        import csv
        import io
        
        if not events:
            return b"# No events to export\n"
        
        # Prepare CSV data
        output = io.StringIO()
        
        # Define CSV columns
        columns = [
            "event_id", "timestamp", "event_type", "user_id", "tool_id",
            "execution_id", "status", "duration_ms", "result_summary",
            "error_message", "ip_address", "user_agent"
        ]
        
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
        
        # Write header
        writer.writeheader()
        
        # Write events
        for event in events:
            # Convert datetime to ISO format
            if "timestamp" in event and isinstance(event["timestamp"], datetime):
                event["timestamp"] = event["timestamp"].isoformat()
            
            # Skip MongoDB internal ID
            if "_id" in event:
                del event["_id"]
            
            writer.writerow(event)
        
        csv_content = output.getvalue()
        
        # Calculate checksum
        checksum = hashlib.sha256(csv_content.encode()).hexdigest()
        
        # Add checksum header
        csv_with_checksum = (
            f"# Audit Trail Export\n"
            f"# Export Timestamp: {datetime.utcnow().isoformat()}\n"
            f"# Event Count: {len(events)}\n"
            f"# Checksum (SHA-256): {checksum}\n"
            f"#\n"
            f"{csv_content}"
        )
        
        logger.info(
            f"Exported {len(events)} audit events as CSV "
            f"(checksum={checksum[:16]}...)"
        )
        
        return csv_with_checksum.encode('utf-8')
    
    async def log_execution_initiated(
        self,
        execution_id: UUID,
        user_id: UUID,
        tool_id: UUID,
        parameters: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Log execution initiation event.
        
        Args:
            execution_id: Execution identifier
            user_id: User identifier
            tool_id: Tool identifier
            parameters: Execution parameters
            ip_address: Client IP address
            user_agent: Client user agent
            
        Requirement: 17.1
        """
        event = AuditEvent(
            event_id=f"{execution_id}_initiated",
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.EXECUTION_INITIATED,
            user_id=user_id,
            tool_id=tool_id,
            execution_id=execution_id,
            parameters=parameters,
            status="initiated",
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        await self.log_execution_event(event)
    
    async def log_execution_status_change(
        self,
        execution_id: UUID,
        user_id: UUID,
        tool_id: UUID,
        old_status: str,
        new_status: str,
        parameters: Dict[str, Any]
    ) -> None:
        """
        Log execution status change event.
        
        Args:
            execution_id: Execution identifier
            user_id: User identifier
            tool_id: Tool identifier
            old_status: Previous status
            new_status: New status
            parameters: Execution parameters
            
        Requirement: 17.2
        """
        event = AuditEvent(
            event_id=f"{execution_id}_status_{new_status}",
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.EXECUTION_STATUS_CHANGED,
            user_id=user_id,
            tool_id=tool_id,
            execution_id=execution_id,
            parameters=parameters,
            status=new_status,
            metadata={
                "old_status": old_status,
                "new_status": new_status
            }
        )
        
        await self.log_execution_event(event)
    
    async def log_execution_completed(
        self,
        execution_id: UUID,
        user_id: UUID,
        tool_id: UUID,
        parameters: Dict[str, Any],
        status: str,
        duration_ms: int,
        resource_usage: ResourceUsage,
        result_summary: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Log execution completion event.
        
        Args:
            execution_id: Execution identifier
            user_id: User identifier
            tool_id: Tool identifier
            parameters: Execution parameters
            status: Final status
            duration_ms: Execution duration in milliseconds
            resource_usage: Resource consumption
            result_summary: Summary of results
            error_message: Error message if failed
            
        Requirement: 17.3
        """
        event_type = (
            AuditEventType.EXECUTION_COMPLETED if status == "success"
            else AuditEventType.EXECUTION_FAILED
        )
        
        event = AuditEvent(
            event_id=f"{execution_id}_completed",
            timestamp=datetime.utcnow(),
            event_type=event_type,
            user_id=user_id,
            tool_id=tool_id,
            execution_id=execution_id,
            parameters=parameters,
            status=status,
            duration_ms=duration_ms,
            resource_usage=resource_usage,
            result_summary=result_summary,
            error_message=error_message
        )
        
        await self.log_execution_event(event)
    
    async def get_execution_audit_trail(
        self,
        execution_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Get complete audit trail for a specific execution.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            List of audit events for the execution
        """
        filters = AuditFilters(
            execution_id=execution_id,
            limit=1000  # Large limit to get all events
        )
        
        return await self.query_audit_trail(filters)
    
    async def get_user_audit_trail(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail for a specific user.
        
        Args:
            user_id: User identifier
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of events
            
        Returns:
            List of audit events for the user
        """
        filters = AuditFilters(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return await self.query_audit_trail(filters)
    
    async def get_tool_audit_trail(
        self,
        tool_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail for a specific tool.
        
        Args:
            tool_id: Tool identifier
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of events
            
        Returns:
            List of audit events for the tool
        """
        filters = AuditFilters(
            tool_id=tool_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return await self.query_audit_trail(filters)


# ============================================================================
# Helper Functions
# ============================================================================


def create_audit_trail_manager(
    mongo_db: AsyncIOMotorDatabase
) -> AuditTrailManager:
    """
    Factory function to create an AuditTrailManager instance.
    
    Args:
        mongo_db: MongoDB database
        
    Returns:
        AuditTrailManager instance
    """
    return AuditTrailManager(mongo_db=mongo_db)
