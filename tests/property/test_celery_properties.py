"""Property-based tests for Celery Task Queue"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from uuid import uuid4, UUID
from datetime import datetime
import asyncio

from app.services.task_tracker import TaskTracker
from app.tasks.ai_tasks import (
    analyze_feasibility_task,
    suggest_improvements_task,
    generate_config_task
)


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def valid_mcp_config(draw):
    """Generate valid MCP configuration dictionaries"""
    return {
        "servers": draw(st.lists(
            st.dictionaries(
                st.sampled_from(["name", "url", "type"]),
                st.text(min_size=1, max_size=50),
                min_size=1,
                max_size=3
            ),
            min_size=0,
            max_size=3
        )),
        "tools": draw(st.lists(
            st.dictionaries(
                st.sampled_from(["name", "description", "version"]),
                st.text(min_size=1, max_size=50),
                min_size=1,
                max_size=3
            ),
            min_size=0,
            max_size=3
        ))
    }


@st.composite
def valid_config_requirements(draw):
    """Generate valid configuration requirements"""
    return {
        "tool_name": draw(st.text(min_size=1, max_size=100)),
        "description": draw(st.text(min_size=1, max_size=200)),
        "capabilities": draw(st.lists(
            st.text(min_size=1, max_size=50),
            min_size=1,
            max_size=5
        )),
        "constraints": draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.text(min_size=1, max_size=50),
            min_size=0,
            max_size=3
        ))
    }


# ============================================================================
# Property Tests
# ============================================================================

# Feature: mcp-platform-backend, Property 33: Async Task Queuing
@given(
    task_type=st.sampled_from([
        "feasibility_analysis",
        "improvement_suggestions",
        "config_generation"
    ]),
    config=valid_mcp_config(),
    requirements=valid_config_requirements()
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_async_task_queuing(
    task_type,
    config,
    requirements,
    task_tracker_fixture
):
    """
    Property 33: Async Task Queuing
    
    For any long-running operation (AI analysis, GitHub sync, embedding generation),
    a Celery task should be created and queued.
    
    This test verifies that:
    1. Tasks can be queued successfully
    2. Task status is tracked in Redis
    3. Tasks are assigned unique IDs
    
    Validates: Requirements 9.1, 9.2, 9.3
    """
    tracker = task_tracker_fixture
    task_id = uuid4()
    
    # Mark task as pending (simulating task queuing)
    await tracker.mark_task_pending(
        task_id=task_id,
        message=f"Queued {task_type} task"
    )
    
    # Verify task status was stored
    task_status = await tracker.get_task_status(task_id)
    
    assert task_status is not None, "Task status should be stored in Redis"
    assert task_status["status"] == "pending", "Task should be in pending state"
    assert "updated_at" in task_status, "Task should have timestamp"
    
    # Simulate task execution by marking as running
    await tracker.mark_task_running(
        task_id=task_id,
        progress=50,
        message=f"Processing {task_type}"
    )
    
    # Verify running status
    running_status = await tracker.get_task_status(task_id)
    assert running_status is not None
    assert running_status["status"] == "running"
    assert running_status.get("progress") == 50
    
    # Simulate task completion
    result = {
        "task_type": task_type,
        "completed": True,
        "data": config if task_type != "config_generation" else requirements
    }
    
    await tracker.mark_task_completed(
        task_id=task_id,
        result=result,
        message=f"Completed {task_type}"
    )
    
    # Verify completed status and result
    completed_info = await tracker.get_task_info(task_id)
    assert completed_info is not None
    assert completed_info["status"] == "completed"
    assert completed_info["progress"] == 100
    assert completed_info["result"] is not None
    assert completed_info["result"]["task_type"] == task_type


# Feature: mcp-platform-backend, Property 33: Task Uniqueness
@given(
    task_count=st.integers(min_value=2, max_value=10)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_task_id_uniqueness(task_count, task_tracker_fixture):
    """
    Property 33: Task ID Uniqueness
    
    For any set of queued tasks, all task IDs should be unique.
    
    Validates: Requirements 9.1, 9.2, 9.3
    """
    tracker = task_tracker_fixture
    
    # Create multiple tasks
    task_ids = [uuid4() for _ in range(task_count)]
    
    # Verify all IDs are unique
    assert len(task_ids) == len(set(task_ids)), "All task IDs should be unique"
    
    # Queue all tasks
    for task_id in task_ids:
        await tracker.mark_task_pending(
            task_id=task_id,
            message="Test task"
        )
    
    # Verify all tasks are tracked independently
    for task_id in task_ids:
        status = await tracker.get_task_status(task_id)
        assert status is not None, f"Task {task_id} should be tracked"
        assert status["status"] == "pending"


# Feature: mcp-platform-backend, Property 33: Task Failure Handling
@given(
    error_message=st.text(min_size=1, max_size=200)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_task_failure_handling(error_message, task_tracker_fixture):
    """
    Property 33: Task Failure Handling
    
    For any task that fails, the failure should be recorded with error details.
    
    Validates: Requirements 9.1, 9.2, 9.3
    """
    tracker = task_tracker_fixture
    task_id = uuid4()
    
    # Queue task
    await tracker.mark_task_pending(task_id=task_id)
    
    # Mark task as failed
    await tracker.mark_task_failed(
        task_id=task_id,
        error=error_message,
        message="Task failed during execution"
    )
    
    # Verify failure is recorded
    task_info = await tracker.get_task_info(task_id)
    
    assert task_info is not None
    assert task_info["status"] == "failed"
    assert task_info["result"] is not None
    assert "error" in task_info["result"]
    assert task_info["result"]["error"] == error_message


# Feature: mcp-platform-backend, Property 33: Task Progress Tracking
@given(
    progress_updates=st.lists(
        st.integers(min_value=0, max_value=100),
        min_size=1,
        max_size=10
    )
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_task_progress_tracking(progress_updates, task_tracker_fixture):
    """
    Property 33: Task Progress Tracking
    
    For any task with progress updates, the latest progress should be retrievable.
    
    Validates: Requirements 9.1, 9.2, 9.3
    """
    tracker = task_tracker_fixture
    task_id = uuid4()
    
    # Queue task
    await tracker.mark_task_pending(task_id=task_id)
    
    # Apply progress updates
    for progress in progress_updates:
        await tracker.mark_task_running(
            task_id=task_id,
            progress=progress,
            message=f"Progress: {progress}%"
        )
    
    # Verify latest progress
    task_status = await tracker.get_task_status(task_id)
    
    assert task_status is not None
    assert task_status["status"] == "running"
    
    if progress_updates:
        # Should have the last progress value
        assert task_status.get("progress") == progress_updates[-1]


# Feature: mcp-platform-backend, Property 33: Task TTL Expiration
@given(
    task_count=st.integers(min_value=1, max_value=5)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_task_ttl_behavior(task_count, task_tracker_fixture):
    """
    Property 33: Task TTL Behavior
    
    For any task stored in Redis, the task should have a TTL set.
    
    Note: This test verifies TTL is set, but doesn't wait for expiration
    as that would make tests too slow.
    
    Validates: Requirements 9.1, 9.2, 9.3
    """
    tracker = task_tracker_fixture
    
    # Create tasks
    task_ids = [uuid4() for _ in range(task_count)]
    
    for task_id in task_ids:
        await tracker.mark_task_pending(task_id=task_id)
        
        # Verify task exists
        status = await tracker.get_task_status(task_id)
        assert status is not None
        
        # Check TTL is set (using Redis client directly)
        key = f"task:{task_id}:status"
        ttl = await tracker.redis.ttl(key)
        
        # TTL should be positive (not -1 which means no expiry)
        assert ttl > 0, f"Task {task_id} should have TTL set"
        assert ttl <= tracker.status_ttl, f"TTL should not exceed configured value"


# Feature: mcp-platform-backend, Property 33: Concurrent Task Handling
@given(
    concurrent_tasks=st.integers(min_value=2, max_value=20)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_concurrent_task_handling(concurrent_tasks, task_tracker_fixture):
    """
    Property 33: Concurrent Task Handling
    
    For any number of concurrent tasks, all should be tracked independently
    without interference.
    
    Validates: Requirements 9.1, 9.2, 9.3
    """
    tracker = task_tracker_fixture
    
    # Create task IDs
    task_ids = [uuid4() for _ in range(concurrent_tasks)]
    
    # Queue all tasks concurrently
    await asyncio.gather(*[
        tracker.mark_task_pending(
            task_id=task_id,
            message=f"Concurrent task {i}"
        )
        for i, task_id in enumerate(task_ids)
    ])
    
    # Verify all tasks are tracked
    statuses = await asyncio.gather(*[
        tracker.get_task_status(task_id)
        for task_id in task_ids
    ])
    
    # All tasks should exist
    assert all(status is not None for status in statuses)
    assert all(status["status"] == "pending" for status in statuses)
    
    # Complete all tasks concurrently with different results
    await asyncio.gather(*[
        tracker.mark_task_completed(
            task_id=task_id,
            result={"task_index": i, "data": f"result_{i}"}
        )
        for i, task_id in enumerate(task_ids)
    ])
    
    # Verify all tasks completed with correct results
    results = await asyncio.gather(*[
        tracker.get_task_info(task_id)
        for task_id in task_ids
    ])
    
    assert all(result is not None for result in results)
    assert all(result["status"] == "completed" for result in results)
    
    # Verify each task has its own unique result
    for i, result in enumerate(results):
        assert result["result"]["task_index"] == i
        assert result["result"]["data"] == f"result_{i}"



# Feature: mcp-platform-backend, Property 34: Task Status Update on Completion
@given(
    task_count=st.integers(min_value=1, max_value=10),
    result_data=st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.one_of(
            st.text(max_size=50),
            st.integers(),
            st.booleans(),
            st.lists(st.text(max_size=20), max_size=5)
        ),
        min_size=1,
        max_size=5
    )
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_task_status_update_on_completion(
    task_count,
    result_data,
    task_tracker_fixture
):
    """
    Property 34: Task Status Update on Completion
    
    For any Celery task, when completed, the task status in Redis should be
    updated to "completed" with the result.
    
    This test verifies that:
    1. Task status transitions from pending -> running -> completed
    2. Result is stored and retrievable
    3. Status includes completion timestamp
    4. Multiple tasks can complete independently
    
    Validates: Requirements 9.4
    """
    tracker = task_tracker_fixture
    
    # Create multiple tasks
    task_ids = [uuid4() for _ in range(task_count)]
    
    # Queue all tasks
    for task_id in task_ids:
        await tracker.mark_task_pending(task_id=task_id)
    
    # Start all tasks
    for task_id in task_ids:
        await tracker.mark_task_running(task_id=task_id, progress=50)
    
    # Complete all tasks with results
    for i, task_id in enumerate(task_ids):
        # Add task-specific data to result
        task_result = {**result_data, "task_index": i}
        await tracker.mark_task_completed(
            task_id=task_id,
            result=task_result
        )
    
    # Verify all tasks are completed with correct status and results
    for i, task_id in enumerate(task_ids):
        task_info = await tracker.get_task_info(task_id)
        
        # Assert task exists
        assert task_info is not None, f"Task {task_id} should exist"
        
        # Assert status is completed
        assert task_info["status"] == "completed", \
            f"Task {task_id} should be completed"
        
        # Assert progress is 100%
        assert task_info["progress"] == 100, \
            f"Completed task should have 100% progress"
        
        # Assert result is stored
        assert task_info["result"] is not None, \
            f"Task {task_id} should have result"
        
        # Assert result contains expected data
        assert task_info["result"]["task_index"] == i, \
            f"Task result should contain correct task_index"
        
        # Assert result contains all original data
        for key, value in result_data.items():
            assert key in task_info["result"], \
                f"Result should contain key '{key}'"
            assert task_info["result"][key] == value, \
                f"Result value for '{key}' should match"
        
        # Assert timestamp exists
        assert "updated_at" in task_info, \
            "Task should have updated_at timestamp"


# Feature: mcp-platform-backend, Property 34: Task Status Transitions
@given(
    transition_count=st.integers(min_value=1, max_value=10)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_task_status_transitions(
    transition_count,
    task_tracker_fixture
):
    """
    Property 34: Task Status Transitions
    
    For any task, status updates should be reflected immediately in Redis.
    
    Validates: Requirements 9.4
    """
    tracker = task_tracker_fixture
    task_id = uuid4()
    
    # Start with pending
    await tracker.mark_task_pending(task_id=task_id)
    status = await tracker.get_task_status(task_id)
    assert status["status"] == "pending"
    
    # Transition through running states with progress updates
    for i in range(transition_count):
        progress = min(10 + (i * 10), 90)  # Progress from 10 to 90
        await tracker.mark_task_running(
            task_id=task_id,
            progress=progress,
            message=f"Processing step {i+1}"
        )
        
        # Verify status updated immediately
        status = await tracker.get_task_status(task_id)
        assert status["status"] == "running"
        assert status["progress"] == progress
    
    # Complete the task
    await tracker.mark_task_completed(
        task_id=task_id,
        result={"transitions": transition_count}
    )
    
    # Verify final status
    final_info = await tracker.get_task_info(task_id)
    assert final_info["status"] == "completed"
    assert final_info["progress"] == 100
    assert final_info["result"]["transitions"] == transition_count


# Feature: mcp-platform-backend, Property 34: Task Result Persistence
@given(
    result_type=st.sampled_from(["dict", "list", "string", "number"]),
    result_size=st.integers(min_value=1, max_value=20)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_task_result_persistence(
    result_type,
    result_size,
    task_tracker_fixture
):
    """
    Property 34: Task Result Persistence
    
    For any task result type (dict, list, string, number), the result should
    be correctly serialized, stored, and retrieved from Redis.
    
    Validates: Requirements 9.4
    """
    tracker = task_tracker_fixture
    task_id = uuid4()
    
    # Generate result based on type
    if result_type == "dict":
        result = {f"key_{i}": f"value_{i}" for i in range(result_size)}
    elif result_type == "list":
        result = [f"item_{i}" for i in range(result_size)]
    elif result_type == "string":
        result = "x" * result_size
    else:  # number
        result = result_size
    
    # Store result
    await tracker.mark_task_completed(
        task_id=task_id,
        result=result
    )
    
    # Retrieve and verify
    retrieved_result = await tracker.get_task_result(task_id)
    
    assert retrieved_result is not None, "Result should be retrievable"
    
    # For non-dict/list types, result is wrapped in {"value": ...}
    if result_type in ["dict", "list"]:
        assert retrieved_result == result, "Result should match original"
    else:
        assert "value" in retrieved_result, "Scalar result should be wrapped"
        assert str(retrieved_result["value"]) == str(result), \
            "Wrapped result should match original"


# Feature: mcp-platform-backend, Property 34: Task Cleanup
@given(
    task_count=st.integers(min_value=1, max_value=10)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_task_cleanup(task_count, task_tracker_fixture):
    """
    Property 34: Task Cleanup
    
    For any completed task, status and result should be deletable from Redis.
    
    Validates: Requirements 9.4
    """
    tracker = task_tracker_fixture
    
    # Create and complete tasks
    task_ids = [uuid4() for _ in range(task_count)]
    
    for i, task_id in enumerate(task_ids):
        await tracker.mark_task_completed(
            task_id=task_id,
            result={"index": i}
        )
    
    # Verify all tasks exist
    for task_id in task_ids:
        info = await tracker.get_task_info(task_id)
        assert info is not None
    
    # Delete all tasks
    for task_id in task_ids:
        status_deleted = await tracker.delete_task_status(task_id)
        result_deleted = await tracker.delete_task_result(task_id)
        
        assert status_deleted or result_deleted, \
            f"At least one deletion should succeed for task {task_id}"
    
    # Verify all tasks are gone
    for task_id in task_ids:
        info = await tracker.get_task_info(task_id)
        assert info is None, f"Task {task_id} should be deleted"
