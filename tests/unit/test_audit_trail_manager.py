"""
Unit tests for Audit Trail Manager.

Tests the audit trail logging, querying, and export functionality.
"""

import pytest
import json
import hashlib
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.audit_trail_manager import (
    AuditTrailManager,
    AuditEvent,
    AuditEventType,
    AuditFilters,
    ResourceUsage,
    create_audit_trail_manager
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_mongo_db():
    """Create mock MongoDB database"""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    
    # Mock collection methods
    mock_collection.insert_one = AsyncMock()
    mock_collection.find = MagicMock()
    mock_collection.create_index = AsyncMock()
    mock_collection.count_documents = AsyncMock(return_value=0)
    
    # Mock cursor
    mock_cursor = MagicMock()
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    mock_cursor.skip = MagicMock(return_value=mock_cursor)
    mock_cursor.limit = MagicMock(return_value=mock_cursor)
    mock_cursor.to_list = AsyncMock(return_value=[])
    
    mock_collection.find.return_value = mock_cursor
    
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)
    
    return mock_db


@pytest.fixture
def audit_manager(mock_mongo_db):
    """Create AuditTrailManager instance"""
    return AuditTrailManager(mock_mongo_db)


@pytest.fixture
def sample_audit_event():
    """Create sample audit event"""
    return AuditEvent(
        event_id="test_event_1",
        timestamp=datetime.utcnow(),
        event_type=AuditEventType.EXECUTION_INITIATED,
        user_id=uuid4(),
        tool_id=uuid4(),
        execution_id=uuid4(),
        parameters={"param1": "value1"},
        status="initiated",
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0"
    )


# ============================================================================
# Test Audit Event Logging
# ============================================================================


@pytest.mark.asyncio
async def test_log_execution_event(audit_manager, sample_audit_event):
    """Test logging an audit event"""
    await audit_manager.log_execution_event(sample_audit_event)
    
    # Verify insert was called
    audit_manager.audit_collection.insert_one.assert_called_once()
    
    # Verify event data
    call_args = audit_manager.audit_collection.insert_one.call_args[0][0]
    assert call_args["event_id"] == sample_audit_event.event_id
    assert call_args["event_type"] == sample_audit_event.event_type.value
    assert call_args["user_id"] == str(sample_audit_event.user_id)
    assert call_args["tool_id"] == str(sample_audit_event.tool_id)
    assert call_args["execution_id"] == str(sample_audit_event.execution_id)
    assert call_args["parameters"] == sample_audit_event.parameters
    assert call_args["status"] == sample_audit_event.status
    assert call_args["ip_address"] == sample_audit_event.ip_address
    assert call_args["user_agent"] == sample_audit_event.user_agent


@pytest.mark.asyncio
async def test_log_execution_event_with_resource_usage(audit_manager):
    """Test logging event with resource usage"""
    resource_usage = ResourceUsage(
        cpu_cores_used=2.0,
        memory_mb_used=512,
        duration_ms=5000
    )
    
    event = AuditEvent(
        event_id="test_event_2",
        timestamp=datetime.utcnow(),
        event_type=AuditEventType.EXECUTION_COMPLETED,
        user_id=uuid4(),
        tool_id=uuid4(),
        execution_id=uuid4(),
        parameters={},
        status="success",
        duration_ms=5000,
        resource_usage=resource_usage
    )
    
    await audit_manager.log_execution_event(event)
    
    # Verify resource usage was included
    call_args = audit_manager.audit_collection.insert_one.call_args[0][0]
    assert "resource_usage" in call_args
    assert call_args["resource_usage"]["cpu_cores_used"] == 2.0
    assert call_args["resource_usage"]["memory_mb_used"] == 512
    assert call_args["resource_usage"]["duration_ms"] == 5000


@pytest.mark.asyncio
async def test_log_execution_initiated(audit_manager):
    """Test logging execution initiation"""
    execution_id = uuid4()
    user_id = uuid4()
    tool_id = uuid4()
    parameters = {"test": "param"}
    
    await audit_manager.log_execution_initiated(
        execution_id=execution_id,
        user_id=user_id,
        tool_id=tool_id,
        parameters=parameters,
        ip_address="10.0.0.1",
        user_agent="TestAgent/1.0"
    )
    
    # Verify event was logged
    audit_manager.audit_collection.insert_one.assert_called_once()
    
    call_args = audit_manager.audit_collection.insert_one.call_args[0][0]
    assert call_args["event_type"] == AuditEventType.EXECUTION_INITIATED.value
    assert call_args["execution_id"] == str(execution_id)
    assert call_args["user_id"] == str(user_id)
    assert call_args["tool_id"] == str(tool_id)
    assert call_args["parameters"] == parameters
    assert call_args["status"] == "initiated"


@pytest.mark.asyncio
async def test_log_execution_status_change(audit_manager):
    """Test logging status change"""
    execution_id = uuid4()
    user_id = uuid4()
    tool_id = uuid4()
    
    await audit_manager.log_execution_status_change(
        execution_id=execution_id,
        user_id=user_id,
        tool_id=tool_id,
        old_status="queued",
        new_status="running",
        parameters={}
    )
    
    # Verify event was logged
    call_args = audit_manager.audit_collection.insert_one.call_args[0][0]
    assert call_args["event_type"] == AuditEventType.EXECUTION_STATUS_CHANGED.value
    assert call_args["status"] == "running"
    assert call_args["metadata"]["old_status"] == "queued"
    assert call_args["metadata"]["new_status"] == "running"


@pytest.mark.asyncio
async def test_log_execution_completed_success(audit_manager):
    """Test logging successful completion"""
    execution_id = uuid4()
    user_id = uuid4()
    tool_id = uuid4()
    resource_usage = ResourceUsage(1.5, 256, 3000)
    
    await audit_manager.log_execution_completed(
        execution_id=execution_id,
        user_id=user_id,
        tool_id=tool_id,
        parameters={},
        status="success",
        duration_ms=3000,
        resource_usage=resource_usage,
        result_summary="Test completed"
    )
    
    # Verify event was logged
    call_args = audit_manager.audit_collection.insert_one.call_args[0][0]
    assert call_args["event_type"] == AuditEventType.EXECUTION_COMPLETED.value
    assert call_args["status"] == "success"
    assert call_args["duration_ms"] == 3000
    assert call_args["result_summary"] == "Test completed"


@pytest.mark.asyncio
async def test_log_execution_completed_failure(audit_manager):
    """Test logging failed completion"""
    execution_id = uuid4()
    user_id = uuid4()
    tool_id = uuid4()
    resource_usage = ResourceUsage(0.5, 128, 1000)
    
    await audit_manager.log_execution_completed(
        execution_id=execution_id,
        user_id=user_id,
        tool_id=tool_id,
        parameters={},
        status="failed",
        duration_ms=1000,
        resource_usage=resource_usage,
        error_message="Test error"
    )
    
    # Verify event was logged
    call_args = audit_manager.audit_collection.insert_one.call_args[0][0]
    assert call_args["event_type"] == AuditEventType.EXECUTION_FAILED.value
    assert call_args["status"] == "failed"
    assert call_args["error_message"] == "Test error"


# ============================================================================
# Test Audit Trail Querying
# ============================================================================


@pytest.mark.asyncio
async def test_query_audit_trail_no_filters(audit_manager):
    """Test querying audit trail without filters"""
    # Mock return data
    mock_events = [
        {
            "event_id": "event1",
            "timestamp": datetime.utcnow(),
            "event_type": "execution_initiated"
        }
    ]
    
    mock_cursor = audit_manager.audit_collection.find.return_value
    mock_cursor.to_list = AsyncMock(return_value=mock_events)
    
    filters = AuditFilters()
    results = await audit_manager.query_audit_trail(filters)
    
    assert len(results) == 1
    assert results[0]["event_id"] == "event1"
    
    # Verify query was called with empty filter
    audit_manager.audit_collection.find.assert_called_once_with({})


@pytest.mark.asyncio
async def test_query_audit_trail_with_user_filter(audit_manager):
    """Test querying by user ID"""
    user_id = uuid4()
    
    filters = AuditFilters(user_id=user_id)
    await audit_manager.query_audit_trail(filters)
    
    # Verify query included user_id
    call_args = audit_manager.audit_collection.find.call_args[0][0]
    assert call_args["user_id"] == str(user_id)


@pytest.mark.asyncio
async def test_query_audit_trail_with_tool_filter(audit_manager):
    """Test querying by tool ID"""
    tool_id = uuid4()
    
    filters = AuditFilters(tool_id=tool_id)
    await audit_manager.query_audit_trail(filters)
    
    # Verify query included tool_id
    call_args = audit_manager.audit_collection.find.call_args[0][0]
    assert call_args["tool_id"] == str(tool_id)


@pytest.mark.asyncio
async def test_query_audit_trail_with_execution_filter(audit_manager):
    """Test querying by execution ID"""
    execution_id = uuid4()
    
    filters = AuditFilters(execution_id=execution_id)
    await audit_manager.query_audit_trail(filters)
    
    # Verify query included execution_id
    call_args = audit_manager.audit_collection.find.call_args[0][0]
    assert call_args["execution_id"] == str(execution_id)


@pytest.mark.asyncio
async def test_query_audit_trail_with_date_range(audit_manager):
    """Test querying with date range"""
    start_date = datetime.utcnow() - timedelta(days=7)
    end_date = datetime.utcnow()
    
    filters = AuditFilters(start_date=start_date, end_date=end_date)
    await audit_manager.query_audit_trail(filters)
    
    # Verify query included date range
    call_args = audit_manager.audit_collection.find.call_args[0][0]
    assert "timestamp" in call_args
    assert "$gte" in call_args["timestamp"]
    assert "$lte" in call_args["timestamp"]
    assert call_args["timestamp"]["$gte"] == start_date
    assert call_args["timestamp"]["$lte"] == end_date


@pytest.mark.asyncio
async def test_query_audit_trail_with_pagination(audit_manager):
    """Test querying with pagination"""
    filters = AuditFilters(limit=50, skip=100)
    await audit_manager.query_audit_trail(filters)
    
    # Verify pagination was applied
    mock_cursor = audit_manager.audit_collection.find.return_value
    mock_cursor.skip.assert_called_once_with(100)
    mock_cursor.limit.assert_called_once_with(50)


@pytest.mark.asyncio
async def test_get_execution_audit_trail(audit_manager):
    """Test getting audit trail for specific execution"""
    execution_id = uuid4()
    
    mock_events = [
        {"event_id": "event1", "event_type": "execution_initiated"},
        {"event_id": "event2", "event_type": "execution_completed"}
    ]
    
    mock_cursor = audit_manager.audit_collection.find.return_value
    mock_cursor.to_list = AsyncMock(return_value=mock_events)
    
    results = await audit_manager.get_execution_audit_trail(execution_id)
    
    assert len(results) == 2
    
    # Verify query filtered by execution_id
    call_args = audit_manager.audit_collection.find.call_args[0][0]
    assert call_args["execution_id"] == str(execution_id)


# ============================================================================
# Test Audit Trail Export
# ============================================================================


@pytest.mark.asyncio
async def test_export_audit_trail_json(audit_manager):
    """Test exporting audit trail as JSON"""
    mock_events = [
        {
            "event_id": "event1",
            "timestamp": datetime(2024, 1, 1, 12, 0, 0),
            "event_type": "execution_initiated",
            "user_id": str(uuid4()),
            "tool_id": str(uuid4()),
            "execution_id": str(uuid4()),
            "parameters": {"test": "param"}
        }
    ]
    
    mock_cursor = audit_manager.audit_collection.find.return_value
    mock_cursor.to_list = AsyncMock(return_value=mock_events)
    
    filters = AuditFilters()
    export_data = await audit_manager.export_audit_trail(filters, format="json")
    
    # Verify it's valid JSON
    parsed = json.loads(export_data.decode('utf-8'))
    
    assert "export_timestamp" in parsed
    assert "event_count" in parsed
    assert "events" in parsed
    assert "checksum" in parsed
    assert "checksum_algorithm" in parsed
    
    assert parsed["event_count"] == 1
    assert parsed["checksum_algorithm"] == "SHA-256"
    assert len(parsed["events"]) == 1


@pytest.mark.asyncio
async def test_export_audit_trail_json_checksum(audit_manager):
    """Test JSON export checksum is correct"""
    mock_events = [
        {
            "event_id": "event1",
            "timestamp": datetime(2024, 1, 1, 12, 0, 0),
            "event_type": "execution_initiated",
            "user_id": str(uuid4()),
            "tool_id": str(uuid4()),
            "execution_id": str(uuid4()),
            "parameters": {}
        }
    ]
    
    mock_cursor = audit_manager.audit_collection.find.return_value
    mock_cursor.to_list = AsyncMock(return_value=mock_events)
    
    filters = AuditFilters()
    export_data = await audit_manager.export_audit_trail(filters, format="json")
    
    parsed = json.loads(export_data.decode('utf-8'))
    
    # Verify checksum
    events_json = json.dumps(parsed["events"], sort_keys=True)
    expected_checksum = hashlib.sha256(events_json.encode()).hexdigest()
    
    assert parsed["checksum"] == expected_checksum


@pytest.mark.asyncio
async def test_export_audit_trail_csv(audit_manager):
    """Test exporting audit trail as CSV"""
    mock_events = [
        {
            "event_id": "event1",
            "timestamp": datetime(2024, 1, 1, 12, 0, 0),
            "event_type": "execution_initiated",
            "user_id": str(uuid4()),
            "tool_id": str(uuid4()),
            "execution_id": str(uuid4()),
            "status": "initiated"
        }
    ]
    
    mock_cursor = audit_manager.audit_collection.find.return_value
    mock_cursor.to_list = AsyncMock(return_value=mock_events)
    
    filters = AuditFilters()
    export_data = await audit_manager.export_audit_trail(filters, format="csv")
    
    csv_text = export_data.decode('utf-8')
    
    # Verify CSV structure
    assert "# Audit Trail Export" in csv_text
    assert "# Export Timestamp:" in csv_text
    assert "# Event Count: 1" in csv_text
    assert "# Checksum (SHA-256):" in csv_text
    assert "event_id,timestamp,event_type" in csv_text
    assert "event1" in csv_text


@pytest.mark.asyncio
async def test_export_audit_trail_invalid_format(audit_manager):
    """Test exporting with invalid format raises error"""
    filters = AuditFilters()
    
    with pytest.raises(ValueError, match="Unsupported export format"):
        await audit_manager.export_audit_trail(filters, format="xml")


@pytest.mark.asyncio
async def test_export_audit_trail_empty(audit_manager):
    """Test exporting empty audit trail"""
    mock_cursor = audit_manager.audit_collection.find.return_value
    mock_cursor.to_list = AsyncMock(return_value=[])
    
    filters = AuditFilters()
    export_data = await audit_manager.export_audit_trail(filters, format="json")
    
    parsed = json.loads(export_data.decode('utf-8'))
    assert parsed["event_count"] == 0
    assert len(parsed["events"]) == 0


# ============================================================================
# Test Helper Functions
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_audit_trail(audit_manager):
    """Test getting user-specific audit trail"""
    user_id = uuid4()
    
    mock_events = [{"event_id": "event1"}]
    mock_cursor = audit_manager.audit_collection.find.return_value
    mock_cursor.to_list = AsyncMock(return_value=mock_events)
    
    results = await audit_manager.get_user_audit_trail(user_id, limit=50)
    
    assert len(results) == 1
    
    # Verify query filtered by user_id
    call_args = audit_manager.audit_collection.find.call_args[0][0]
    assert call_args["user_id"] == str(user_id)


@pytest.mark.asyncio
async def test_get_tool_audit_trail(audit_manager):
    """Test getting tool-specific audit trail"""
    tool_id = uuid4()
    
    mock_events = [{"event_id": "event1"}]
    mock_cursor = audit_manager.audit_collection.find.return_value
    mock_cursor.to_list = AsyncMock(return_value=mock_events)
    
    results = await audit_manager.get_tool_audit_trail(tool_id, limit=50)
    
    assert len(results) == 1
    
    # Verify query filtered by tool_id
    call_args = audit_manager.audit_collection.find.call_args[0][0]
    assert call_args["tool_id"] == str(tool_id)


def test_create_audit_trail_manager(mock_mongo_db):
    """Test factory function"""
    manager = create_audit_trail_manager(mock_mongo_db)
    
    assert isinstance(manager, AuditTrailManager)
    assert manager.mongo == mock_mongo_db


# ============================================================================
# Test Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_log_execution_event_error_handling(audit_manager):
    """Test that logging errors don't raise exceptions"""
    # Make insert_one raise an exception
    audit_manager.audit_collection.insert_one = AsyncMock(
        side_effect=Exception("Database error")
    )
    
    event = AuditEvent(
        event_id="test",
        timestamp=datetime.utcnow(),
        event_type=AuditEventType.EXECUTION_INITIATED,
        user_id=uuid4(),
        tool_id=uuid4(),
        execution_id=uuid4(),
        parameters={}
    )
    
    # Should not raise exception
    await audit_manager.log_execution_event(event)


@pytest.mark.asyncio
async def test_query_audit_trail_error_handling(audit_manager):
    """Test query error handling"""
    # Make find raise an exception
    audit_manager.audit_collection.find = MagicMock(
        side_effect=Exception("Query error")
    )
    
    filters = AuditFilters()
    
    # Should raise exception for queries
    with pytest.raises(Exception, match="Query error"):
        await audit_manager.query_audit_trail(filters)


# ============================================================================
# Test Index Creation
# ============================================================================


@pytest.mark.asyncio
async def test_ensure_indexes_creates_indexes(audit_manager):
    """Test that indexes are created on first use"""
    # Trigger index creation
    await audit_manager._ensure_indexes()
    
    # Verify create_index was called multiple times
    assert audit_manager.audit_collection.create_index.call_count >= 6


@pytest.mark.asyncio
async def test_ensure_indexes_only_once(audit_manager):
    """Test that indexes are only created once"""
    # Call twice
    await audit_manager._ensure_indexes()
    call_count_1 = audit_manager.audit_collection.create_index.call_count
    
    await audit_manager._ensure_indexes()
    call_count_2 = audit_manager.audit_collection.create_index.call_count
    
    # Should be the same (not called again)
    assert call_count_1 == call_count_2
