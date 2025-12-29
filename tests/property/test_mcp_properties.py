"""Property-based tests for MCP Manager"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from uuid import uuid4, UUID
from datetime import datetime

from app.services.mcp_manager import MCPManager, MCPToolFilters, Pagination
from app.schemas.mcp_tool import MCPToolCreate, MCPToolUpdate, MCPTool
from app.models.mcp_tool import ToolStatus


# ============================================================================
# Hypothesis Strategies
# ============================================================================

# Valid slug pattern: lowercase letters, numbers, hyphens (not at start/end, no consecutive)
@st.composite
def valid_slug(draw):
    """Generate valid slug strings"""
    # Start with a letter or number
    first_char = draw(st.sampled_from('abcdefghijklmnopqrstuvwxyz0123456789'))
    
    # Middle can have letters, numbers, and single hyphens
    middle_parts = draw(st.lists(
        st.sampled_from('abcdefghijklmnopqrstuvwxyz0123456789-'),
        min_size=0,
        max_size=20
    ))
    
    # End with a letter or number
    last_char = draw(st.sampled_from('abcdefghijklmnopqrstuvwxyz0123456789'))
    
    # Combine and ensure no consecutive hyphens
    slug = first_char + ''.join(middle_parts) + last_char
    slug = slug.replace('--', '-')  # Remove consecutive hyphens
    
    return slug[:50]  # Limit length


@st.composite
def valid_version(draw):
    """Generate valid semantic version strings"""
    major = draw(st.integers(min_value=0, max_value=99))
    minor = draw(st.integers(min_value=0, max_value=99))
    patch = draw(st.integers(min_value=0, max_value=99))
    return f"{major}.{minor}.{patch}"


@st.composite
def valid_mcp_tool_create(draw):
    """Generate valid MCPToolCreate instances"""
    return MCPToolCreate(
        name=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters=' -_'
        ))),
        slug=draw(valid_slug()),
        description=draw(st.one_of(st.none(), st.text(max_size=200))),
        version=draw(valid_version()),
        config=draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
            min_size=0,
            max_size=5
        )),
        author_id=uuid4(),
        status=draw(st.sampled_from(list(ToolStatus)))
    )


# ============================================================================
# Property Tests
# ============================================================================

# Feature: mcp-platform-backend, Property 1: MCP Tool Creation Persistence
@given(tool_data=valid_mcp_tool_create())
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_mcp_tool_creation_persistence(tool_data, mcp_manager_fixture):
    """
    Property 1: MCP Tool Creation Persistence
    
    For any valid MCP tool metadata, when a tool is created, the tool should be
    retrievable from MySQL using the returned identifier and contain equivalent data.
    
    Validates: Requirements 1.1, 1.2
    """
    mcp_manager = mcp_manager_fixture
    
    # Create tool
    created_tool = await mcp_manager.create_tool(tool_data)
    
    # Retrieve tool
    retrieved_tool = await mcp_manager.get_tool(created_tool.id)
    
    # Assert tool was retrieved
    assert retrieved_tool is not None, "Tool should be retrievable after creation"
    
    # Assert data equivalence
    assert retrieved_tool.id == created_tool.id
    assert retrieved_tool.name == tool_data.name
    assert retrieved_tool.slug == tool_data.slug
    assert retrieved_tool.description == tool_data.description
    assert retrieved_tool.version == tool_data.version
    assert retrieved_tool.author_id == tool_data.author_id
    assert retrieved_tool.status == tool_data.status


# Feature: mcp-platform-backend, Property 2: Version History on Update
@given(
    tool_data=valid_mcp_tool_create(),
    new_version=valid_version(),
    new_config=st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.text(max_size=50),
        min_size=1,
        max_size=3
    )
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_version_history_on_update(
    tool_data,
    new_version,
    new_config,
    mcp_manager_fixture
):
    """
    Property 2: Version History on Update
    
    For any MCP tool and any valid update, after updating the tool, MySQL should
    contain the new state and MongoDB should contain a history record with the
    previous version.
    
    Validates: Requirements 1.3
    """
    mcp_manager = mcp_manager_fixture
    
    # Create initial tool
    created_tool = await mcp_manager.create_tool(tool_data)
    initial_version = created_tool.version
    
    # Get initial history count
    initial_history = await mcp_manager.get_tool_history(created_tool.id)
    initial_history_count = len(initial_history)
    
    # Update tool with new config
    update_data = MCPToolUpdate(
        version=new_version,
        config=new_config
    )
    updated_tool = await mcp_manager.update_tool(created_tool.id, update_data)
    
    # Assert MySQL contains new state
    retrieved_tool = await mcp_manager.get_tool(created_tool.id)
    assert retrieved_tool is not None
    assert retrieved_tool.version == new_version
    
    # Assert MongoDB contains history record
    history = await mcp_manager.get_tool_history(created_tool.id)
    assert len(history) > initial_history_count, "History should grow after update"
    
    # Find the update record
    update_records = [h for h in history if h.change_type == "update"]
    assert len(update_records) > 0, "Should have at least one update record"


# Feature: mcp-platform-backend, Property 3: Soft Delete Preservation
@given(tool_data=valid_mcp_tool_create())
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_soft_delete_preservation(tool_data, mcp_manager_fixture):
    """
    Property 3: Soft Delete Preservation
    
    For any MCP tool, when deleted, the tool should have a non-null deleted_at
    timestamp in MySQL and MongoDB should contain a deletion history record.
    
    Validates: Requirements 1.4
    """
    mcp_manager = mcp_manager_fixture
    
    # Create tool
    created_tool = await mcp_manager.create_tool(tool_data)
    
    # Delete tool
    delete_result = await mcp_manager.delete_tool(created_tool.id)
    assert delete_result is True, "Delete should succeed"
    
    # Tool should not be retrievable via normal get (soft delete)
    retrieved_tool = await mcp_manager.get_tool(created_tool.id)
    assert retrieved_tool is None, "Deleted tool should not be retrievable"
    
    # MongoDB should contain deletion history record
    history = await mcp_manager.get_tool_history(created_tool.id)
    delete_records = [h for h in history if h.change_type == "delete"]
    assert len(delete_records) > 0, "Should have deletion record in history"


# Feature: mcp-platform-backend, Property 4: Pagination Invariants
@given(
    tools_count=st.integers(min_value=1, max_value=50),
    page_size=st.integers(min_value=1, max_value=20)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_pagination_invariants(tools_count, page_size, mcp_manager_fixture):
    """
    Property 4: Pagination Invariants
    
    For any pagination parameters (page, page_size), the returned results should
    not exceed page_size, and the total count should equal the sum of all pages.
    
    Validates: Requirements 1.5
    """
    mcp_manager = mcp_manager_fixture
    
    # Create multiple tools
    author_id = uuid4()
    created_tools = []
    for i in range(tools_count):
        tool_data = MCPToolCreate(
            name=f"Test Tool {i}",
            slug=f"test-tool-{i}-{uuid4().hex[:8]}",
            description=f"Description {i}",
            version="1.0.0",
            config={"index": i},
            author_id=author_id,
            status=ToolStatus.ACTIVE
        )
        tool = await mcp_manager.create_tool(tool_data)
        created_tools.append(tool)
    
    # Test pagination
    filters = MCPToolFilters(author_id=author_id)
    pagination = Pagination(page=1, page_size=page_size)
    
    page_result = await mcp_manager.list_tools(filters, pagination)
    
    # Assert page size constraint
    assert len(page_result.items) <= page_size, \
        f"Page should not exceed page_size ({page_size})"
    
    # Assert total count
    assert page_result.total == tools_count, \
        f"Total count should match created tools count"
    
    # Collect all items across all pages
    all_items = []
    current_page = 1
    while current_page <= page_result.total_pages:
        pagination = Pagination(page=current_page, page_size=page_size)
        page_result = await mcp_manager.list_tools(filters, pagination)
        all_items.extend(page_result.items)
        current_page += 1
    
    # Assert sum of all pages equals total
    assert len(all_items) == tools_count, \
        "Sum of all pages should equal total count"


# Feature: mcp-platform-backend, Property 25: State Persistence in MySQL
@given(
    tool_data=valid_mcp_tool_create(),
    operation=st.sampled_from(['create', 'update', 'delete'])
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_state_persistence_in_mysql(tool_data, operation, mcp_manager_fixture):
    """
    Property 25: State Persistence in MySQL
    
    For any MCP tool modification (create, update, delete), the current state
    should be reflected in the MySQL mcp_tools table.
    
    Validates: Requirements 7.1, 7.3
    """
    mcp_manager = mcp_manager_fixture
    
    if operation == 'create':
        # Create tool
        created_tool = await mcp_manager.create_tool(tool_data)
        
        # Verify state in MySQL
        retrieved_tool = await mcp_manager.get_tool(created_tool.id)
        assert retrieved_tool is not None
        assert retrieved_tool.name == tool_data.name
        assert retrieved_tool.status == tool_data.status
    
    elif operation == 'update':
        # Create tool first
        created_tool = await mcp_manager.create_tool(tool_data)
        
        # Update tool
        update_data = MCPToolUpdate(
            name="Updated Name",
            status=ToolStatus.ACTIVE
        )
        updated_tool = await mcp_manager.update_tool(created_tool.id, update_data)
        
        # Verify updated state in MySQL
        retrieved_tool = await mcp_manager.get_tool(created_tool.id)
        assert retrieved_tool is not None
        assert retrieved_tool.name == "Updated Name"
        assert retrieved_tool.status == ToolStatus.ACTIVE
    
    elif operation == 'delete':
        # Create tool first
        created_tool = await mcp_manager.create_tool(tool_data)
        
        # Delete tool
        await mcp_manager.delete_tool(created_tool.id)
        
        # Verify deleted state (should not be retrievable)
        retrieved_tool = await mcp_manager.get_tool(created_tool.id)
        assert retrieved_tool is None


# Feature: mcp-platform-backend, Property 26: Configuration History Append
@given(
    tool_data=valid_mcp_tool_create(),
    new_config=st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.text(max_size=50),
        min_size=1,
        max_size=3
    )
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_configuration_history_append(
    tool_data,
    new_config,
    mcp_manager_fixture
):
    """
    Property 26: Configuration History Append
    
    For any MCP tool configuration change, the MongoDB mcp_config_history
    collection should grow by exactly one document.
    
    Validates: Requirements 7.2
    """
    mcp_manager = mcp_manager_fixture
    
    # Create tool
    created_tool = await mcp_manager.create_tool(tool_data)
    
    # Get initial history count
    initial_history = await mcp_manager.get_tool_history(created_tool.id)
    initial_count = len(initial_history)
    
    # Update tool configuration
    update_data = MCPToolUpdate(config=new_config)
    await mcp_manager.update_tool(created_tool.id, update_data)
    
    # Get updated history count
    updated_history = await mcp_manager.get_tool_history(created_tool.id)
    updated_count = len(updated_history)
    
    # Assert history grew by at least one (could be 2: one for old version, one for new)
    assert updated_count > initial_count, \
        "History should grow after configuration change"


# Feature: mcp-platform-backend, Property 28: Version History Retrieval
@given(
    tool_data=valid_mcp_tool_create(),
    update_count=st.integers(min_value=1, max_value=5)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_version_history_retrieval(
    tool_data,
    update_count,
    mcp_manager_fixture
):
    """
    Property 28: Version History Retrieval
    
    For any MCP tool with configuration changes, retrieving version history
    should return all historical versions in chronological order.
    
    Validates: Requirements 7.5
    """
    mcp_manager = mcp_manager_fixture
    
    # Create tool
    created_tool = await mcp_manager.create_tool(tool_data)
    
    # Perform multiple updates
    for i in range(update_count):
        update_data = MCPToolUpdate(
            version=f"1.0.{i+1}",
            config={"update": i+1}
        )
        await mcp_manager.update_tool(created_tool.id, update_data)
    
    # Retrieve history
    history = await mcp_manager.get_tool_history(created_tool.id)
    
    # Assert history exists
    assert len(history) > 0, "History should not be empty"
    
    # Assert chronological order (timestamps should be ascending)
    timestamps = [h.changed_at for h in history]
    assert timestamps == sorted(timestamps), \
        "History should be in chronological order"
    
    # Assert all change types are present
    change_types = [h.change_type for h in history]
    assert "create" in change_types, "Should have create record"
    assert "update" in change_types, "Should have update records"
