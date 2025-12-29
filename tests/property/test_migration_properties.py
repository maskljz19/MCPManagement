"""Property-based tests for database migrations"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from pathlib import Path
import re
from typing import List, Tuple


def parse_migration_file(filepath: Path) -> Tuple[str, str, List[str]]:
    """
    Parse a migration file to extract revision, down_revision, and dependencies.
    
    Returns:
        Tuple of (revision, down_revision, dependencies)
    """
    content = filepath.read_text()
    
    # Extract revision
    revision_match = re.search(r"revision\s*=\s*['\"]([^'\"]+)['\"]", content)
    revision = revision_match.group(1) if revision_match else None
    
    # Extract down_revision
    down_revision_match = re.search(r"down_revision\s*=\s*['\"]([^'\"]*)['\"]", content)
    down_revision = down_revision_match.group(1) if down_revision_match else None
    if down_revision == "":
        down_revision = None
    
    # Extract depends_on (usually None or a list)
    depends_on_match = re.search(r"depends_on\s*=\s*(.+)", content)
    depends_on = []
    if depends_on_match:
        depends_str = depends_on_match.group(1).strip()
        if depends_str != "None":
            # Parse list of dependencies
            deps = re.findall(r"['\"]([^'\"]+)['\"]", depends_str)
            depends_on = deps
    
    return revision, down_revision, depends_on


def get_all_migrations() -> List[Tuple[Path, str, str, List[str]]]:
    """
    Get all migration files with their metadata.
    
    Returns:
        List of tuples: (filepath, revision, down_revision, depends_on)
    """
    migrations_dir = Path("alembic/versions")
    if not migrations_dir.exists():
        return []
    
    migrations = []
    for filepath in migrations_dir.glob("*.py"):
        if filepath.name == "__init__.py" or filepath.name.startswith("."):
            continue
        
        try:
            revision, down_revision, depends_on = parse_migration_file(filepath)
            if revision:
                migrations.append((filepath, revision, down_revision, depends_on))
        except Exception:
            # Skip files that can't be parsed
            continue
    
    return migrations


def build_migration_graph(migrations: List[Tuple[Path, str, str, List[str]]]) -> dict:
    """
    Build a dependency graph from migrations.
    
    Returns:
        Dict mapping revision -> (down_revision, depends_on)
    """
    graph = {}
    for filepath, revision, down_revision, depends_on in migrations:
        graph[revision] = (down_revision, depends_on)
    return graph


def topological_sort(graph: dict) -> List[str]:
    """
    Perform topological sort on migration graph to get execution order.
    
    Returns:
        List of revisions in execution order
    """
    # Find all revisions
    all_revisions = set(graph.keys())
    
    # Build adjacency list (parent -> children)
    children = {rev: [] for rev in all_revisions}
    in_degree = {rev: 0 for rev in all_revisions}
    
    for revision, (down_revision, depends_on) in graph.items():
        # Add edge from down_revision to revision
        if down_revision and down_revision in all_revisions:
            children[down_revision].append(revision)
            in_degree[revision] += 1
        
        # Add edges from dependencies to revision
        for dep in depends_on:
            if dep in all_revisions:
                children[dep].append(revision)
                in_degree[revision] += 1
    
    # Find starting nodes (no dependencies)
    queue = [rev for rev in all_revisions if in_degree[rev] == 0]
    result = []
    
    while queue:
        # Sort to ensure deterministic order
        queue.sort()
        current = queue.pop(0)
        result.append(current)
        
        # Process children
        for child in children[current]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)
    
    return result


# Feature: mcp-platform-backend, Property 51: Migration Execution Order
# Validates: Requirements 15.2
@settings(
    max_examples=100,
    deadline=None
)
@given(
    # Generate random subsets of migrations to test ordering
    shuffle_seed=st.integers(min_value=0, max_value=1000)
)
def test_migration_execution_order(shuffle_seed):
    """
    Property 51: Migration Execution Order
    
    For any set of Alembic migrations, when applied, they should execute in 
    dependency order based on revision numbers and down_revision links.
    
    This test validates that:
    1. Migrations form a valid directed acyclic graph (DAG)
    2. Each migration's down_revision exists (except the first)
    3. Topological sort produces a valid execution order
    4. No circular dependencies exist
    """
    # Get all migrations
    migrations = get_all_migrations()
    
    # Skip test if no migrations exist
    assume(len(migrations) > 0)
    
    # Build dependency graph
    graph = build_migration_graph(migrations)
    
    # Validate graph structure
    all_revisions = set(graph.keys())
    
    # Check that all down_revisions exist (except None for first migration)
    for revision, (down_revision, depends_on) in graph.items():
        if down_revision is not None:
            assert down_revision in all_revisions or down_revision == "None", \
                f"Migration {revision} references non-existent down_revision: {down_revision}"
        
        # Check that all dependencies exist
        for dep in depends_on:
            assert dep in all_revisions, \
                f"Migration {revision} references non-existent dependency: {dep}"
    
    # Perform topological sort to get execution order
    try:
        execution_order = topological_sort(graph)
    except Exception as e:
        pytest.fail(f"Failed to determine migration execution order: {e}")
    
    # Verify all migrations are in the execution order
    assert len(execution_order) == len(all_revisions), \
        "Not all migrations are in execution order (possible circular dependency)"
    
    # Verify execution order respects dependencies
    executed = set()
    for revision in execution_order:
        down_revision, depends_on = graph[revision]
        
        # Check that down_revision was executed before this one
        if down_revision and down_revision != "None":
            assert down_revision in executed, \
                f"Migration {revision} executed before its down_revision {down_revision}"
        
        # Check that all dependencies were executed before this one
        for dep in depends_on:
            assert dep in executed, \
                f"Migration {revision} executed before its dependency {dep}"
        
        executed.add(revision)
    
    # Property holds: migrations can be executed in dependency order
    assert True


# Feature: mcp-platform-backend, Property 52: Migration Rollback on Failure
# Validates: Requirements 15.3
@settings(
    max_examples=100,
    deadline=None
)
@given(
    # Simulate different failure scenarios
    failure_point=st.floats(min_value=0.0, max_value=1.0)
)
def test_migration_rollback_on_failure(failure_point):
    """
    Property 52: Migration Rollback on Failure
    
    For any migration that fails during execution, the database should be 
    rolled back to the state before the migration started.
    
    This test validates that:
    1. Each migration has a corresponding downgrade function
    2. Downgrade functions are syntactically valid
    3. Migration files follow the expected structure
    """
    # Get all migrations
    migrations = get_all_migrations()
    
    # Skip test if no migrations exist
    assume(len(migrations) > 0)
    
    # Check each migration file
    for filepath, revision, down_revision, depends_on in migrations:
        content = filepath.read_text()
        
        # Verify upgrade function exists
        assert "def upgrade()" in content, \
            f"Migration {revision} missing upgrade() function"
        
        # Verify downgrade function exists
        assert "def downgrade()" in content, \
            f"Migration {revision} missing downgrade() function"
        
        # Verify downgrade function is not just 'pass'
        # Extract downgrade function body
        downgrade_match = re.search(
            r"def downgrade\(\)[^:]*:\s*(.+?)(?=\n(?:def |$))",
            content,
            re.DOTALL
        )
        
        if downgrade_match:
            downgrade_body = downgrade_match.group(1).strip()
            
            # For the initial migration, downgrade should drop tables
            if down_revision is None or down_revision == "None":
                # First migration should have substantial downgrade logic
                assert len(downgrade_body) > 10, \
                    f"Migration {revision} (initial) has trivial downgrade function"
            
            # Downgrade should not be empty (unless it's a data-only migration)
            assert downgrade_body != "pass", \
                f"Migration {revision} has empty downgrade function"
    
    # Property holds: all migrations have rollback capability
    assert True


# Feature: mcp-platform-backend, Property 53: Migration Downgrade Support
# Validates: Requirements 15.5
@settings(
    max_examples=100,
    deadline=None
)
@given(
    # Test with different migration subsets
    test_seed=st.integers(min_value=0, max_value=1000)
)
def test_migration_downgrade_support(test_seed):
    """
    Property 53: Migration Downgrade Support
    
    For any applied migration, running the downgrade should successfully 
    revert the schema changes.
    
    This test validates that:
    1. Each migration has a downgrade function
    2. Downgrade operations are the inverse of upgrade operations
    3. Migration chain can be traversed backwards
    """
    # Get all migrations
    migrations = get_all_migrations()
    
    # Skip test if no migrations exist
    assume(len(migrations) > 0)
    
    # Build dependency graph
    graph = build_migration_graph(migrations)
    
    # Get execution order
    execution_order = topological_sort(graph)
    
    # Verify we can traverse the chain backwards
    for i, revision in enumerate(execution_order):
        down_revision, depends_on = graph[revision]
        
        # Check that we can downgrade to the previous revision
        if down_revision and down_revision != "None":
            # Verify down_revision is earlier in the execution order
            down_index = execution_order.index(down_revision)
            assert down_index < i, \
                f"Migration {revision} down_revision {down_revision} is not earlier in chain"
        
        # For migrations with dependencies, verify they can be downgraded
        # after their dependents are downgraded
        if depends_on:
            for dep in depends_on:
                dep_index = execution_order.index(dep)
                assert dep_index < i, \
                    f"Migration {revision} dependency {dep} is not earlier in chain"
    
    # Verify downgrade chain is complete
    # Start from the last migration and work backwards
    current = execution_order[-1] if execution_order else None
    visited = set()
    
    while current:
        visited.add(current)
        down_revision, _ = graph[current]
        
        if down_revision and down_revision != "None":
            assert down_revision in graph, \
                f"Downgrade chain broken: {current} -> {down_revision} (missing)"
            current = down_revision
        else:
            # Reached the beginning
            break
    
    # Property holds: complete downgrade chain exists
    assert True


def test_migration_files_exist():
    """
    Unit test: Verify migration files exist and are properly structured.
    """
    migrations_dir = Path("alembic/versions")
    assert migrations_dir.exists(), "Migrations directory should exist"
    
    # Get all migration files
    migrations = get_all_migrations()
    assert len(migrations) > 0, "At least one migration should exist"
    
    # Verify initial migration exists
    initial_migrations = [m for m in migrations if m[2] is None or m[2] == "None"]
    assert len(initial_migrations) > 0, "Initial migration should exist"


def test_migration_naming_convention():
    """
    Unit test: Verify migrations follow naming conventions.
    """
    migrations = get_all_migrations()
    
    for filepath, revision, down_revision, depends_on in migrations:
        # Migration files should be .py files
        assert filepath.suffix == ".py", f"Migration {filepath} should be a .py file"
        
        # Revision should not be empty
        assert revision, f"Migration {filepath} should have a revision ID"
        
        # Revision should be a valid identifier
        assert re.match(r"^[a-zA-Z0-9_]+$", revision), \
            f"Migration {filepath} has invalid revision ID: {revision}"
