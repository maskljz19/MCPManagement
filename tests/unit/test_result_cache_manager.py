"""Unit tests for Result Cache Manager"""

import pytest
import asyncio
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.result_cache_manager import (
    ResultCacheManager,
    CachedResult,
    CacheStats
)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client"""
    redis = AsyncMock()
    
    # Mock storage
    redis._storage = {}
    redis._sorted_sets = {}
    redis._hashes = {}
    
    # Mock basic operations
    async def mock_setex(key, ttl, value):
        redis._storage[key] = {"value": value, "ttl": ttl}
    
    async def mock_get(key):
        if key in redis._storage:
            return redis._storage[key]["value"]
        return None
    
    async def mock_delete(*keys):
        for key in keys:
            redis._storage.pop(key, None)
        return len(keys)
    
    async def mock_exists(key):
        return 1 if key in redis._storage else 0
    
    async def mock_ttl(key):
        if key in redis._storage:
            return redis._storage[key].get("ttl", -1)
        return -1
    
    async def mock_zadd(key, mapping):
        if key not in redis._sorted_sets:
            redis._sorted_sets[key] = {}
        redis._sorted_sets[key].update(mapping)
    
    async def mock_zcard(key):
        return len(redis._sorted_sets.get(key, {}))
    
    async def mock_zrange(key, start, end, withscores=False):
        if key not in redis._sorted_sets:
            return []
        sorted_items = sorted(
            redis._sorted_sets[key].items(),
            key=lambda x: x[1]
        )
        result = [item[0] for item in sorted_items[start:end+1]]
        return result
    
    async def mock_zrem(key, *members):
        if key in redis._sorted_sets:
            for member in members:
                redis._sorted_sets[key].pop(member, None)
        return len(members)
    
    async def mock_scan(cursor, match=None, count=100):
        keys = list(redis._storage.keys())
        if match:
            # Simple pattern matching
            pattern = match.replace("*", "")
            keys = [k for k in keys if k.startswith(pattern)]
        return (0, keys)
    
    async def mock_hincrby(key, field, increment):
        if key not in redis._hashes:
            redis._hashes[key] = {}
        current = int(redis._hashes[key].get(field, 0))
        redis._hashes[key][field] = str(current + increment)
        return current + increment
    
    async def mock_hgetall(key):
        return redis._hashes.get(key, {})
    
    async def mock_memory_usage(key):
        if key in redis._storage:
            return len(str(redis._storage[key]["value"]))
        return None
    
    redis.setex = mock_setex
    redis.get = mock_get
    redis.delete = mock_delete
    redis.exists = mock_exists
    redis.ttl = mock_ttl
    redis.zadd = mock_zadd
    redis.zcard = mock_zcard
    redis.zrange = mock_zrange
    redis.zrem = mock_zrem
    redis.scan = mock_scan
    redis.hincrby = mock_hincrby
    redis.hgetall = mock_hgetall
    redis.memory_usage = mock_memory_usage
    
    return redis


@pytest.fixture
def cache_manager(mock_redis):
    """Create a ResultCacheManager instance with mock Redis"""
    return ResultCacheManager(mock_redis)


class TestCacheKeyGeneration:
    """Test cache key generation (Requirement 10.1)"""
    
    def test_generate_cache_key_deterministic(self):
        """Test that cache key generation is deterministic"""
        tool_id = uuid4()
        tool_name = "test_tool"
        arguments = {"param1": "value1", "param2": "value2"}
        
        key1 = ResultCacheManager.generate_cache_key(tool_id, tool_name, arguments)
        key2 = ResultCacheManager.generate_cache_key(tool_id, tool_name, arguments)
        
        assert key1 == key2
    
    def test_generate_cache_key_order_independent(self):
        """Test that argument order doesn't affect cache key"""
        tool_id = uuid4()
        tool_name = "test_tool"
        arguments1 = {"param1": "value1", "param2": "value2"}
        arguments2 = {"param2": "value2", "param1": "value1"}
        
        key1 = ResultCacheManager.generate_cache_key(tool_id, tool_name, arguments1)
        key2 = ResultCacheManager.generate_cache_key(tool_id, tool_name, arguments2)
        
        assert key1 == key2
    
    def test_generate_cache_key_different_for_different_inputs(self):
        """Test that different inputs produce different cache keys"""
        tool_id1 = uuid4()
        tool_id2 = uuid4()
        tool_name = "test_tool"
        arguments = {"param1": "value1"}
        
        key1 = ResultCacheManager.generate_cache_key(tool_id1, tool_name, arguments)
        key2 = ResultCacheManager.generate_cache_key(tool_id2, tool_name, arguments)
        
        assert key1 != key2
    
    def test_generate_cache_key_handles_complex_arguments(self):
        """Test cache key generation with complex nested arguments"""
        tool_id = uuid4()
        tool_name = "test_tool"
        arguments = {
            "param1": "value1",
            "param2": {"nested": "value"},
            "param3": [1, 2, 3]
        }
        
        key = ResultCacheManager.generate_cache_key(tool_id, tool_name, arguments)
        
        assert isinstance(key, str)
        assert len(key) == 64  # SHA256 produces 64 character hex string


class TestCacheStorage:
    """Test cache storage operations (Requirement 10.1)"""
    
    @pytest.mark.asyncio
    async def test_store_result(self, cache_manager, mock_redis):
        """Test storing a result in cache"""
        cache_key = "test_cache_key"
        result = {"output": "test result"}
        tool_id = uuid4()
        tool_name = "test_tool"
        ttl = 3600
        
        await cache_manager.store_result(cache_key, result, tool_id, tool_name, ttl)
        
        # Verify result was stored
        result_key = f"{cache_manager.RESULT_PREFIX}{cache_key}"
        assert result_key in mock_redis._storage
        
        # Verify LRU tracking was updated
        assert cache_key in mock_redis._sorted_sets.get(cache_manager.LRU_KEY, {})
    
    @pytest.mark.asyncio
    async def test_store_result_uses_default_ttl(self, cache_manager, mock_redis):
        """Test that default TTL is used when not specified"""
        cache_key = "test_cache_key"
        result = {"output": "test result"}
        tool_id = uuid4()
        tool_name = "test_tool"
        
        await cache_manager.store_result(cache_key, result, tool_id, tool_name)
        
        result_key = f"{cache_manager.RESULT_PREFIX}{cache_key}"
        assert mock_redis._storage[result_key]["ttl"] == cache_manager.DEFAULT_TTL


class TestCacheRetrieval:
    """Test cache retrieval operations (Requirement 10.2, 10.3)"""
    
    @pytest.mark.asyncio
    async def test_get_cached_result_hit(self, cache_manager, mock_redis):
        """Test retrieving a cached result (cache hit)"""
        cache_key = "test_cache_key"
        result = {"output": "test result"}
        tool_id = uuid4()
        tool_name = "test_tool"
        
        # Store result first
        await cache_manager.store_result(cache_key, result, tool_id, tool_name)
        
        # Retrieve result
        cached_result = await cache_manager.get_cached_result(cache_key)
        
        assert cached_result is not None
        assert cached_result.result == result
        assert cached_result.tool_id == tool_id
        assert cached_result.tool_name == tool_name
        assert cached_result.cache_key == cache_key
    
    @pytest.mark.asyncio
    async def test_get_cached_result_miss(self, cache_manager, mock_redis):
        """Test retrieving a non-existent result (cache miss)"""
        cache_key = "nonexistent_key"
        
        cached_result = await cache_manager.get_cached_result(cache_key)
        
        assert cached_result is None
    
    @pytest.mark.asyncio
    async def test_get_cached_result_includes_metadata(self, cache_manager, mock_redis):
        """Test that cached result includes metadata (Requirement 10.3)"""
        cache_key = "test_cache_key"
        result = {"output": "test result"}
        tool_id = uuid4()
        tool_name = "test_tool"
        
        await cache_manager.store_result(cache_key, result, tool_id, tool_name)
        cached_result = await cache_manager.get_cached_result(cache_key)
        
        assert cached_result is not None
        assert hasattr(cached_result, "cached_at")
        assert hasattr(cached_result, "cache_key")
        assert hasattr(cached_result, "ttl_seconds")
        assert hasattr(cached_result, "hit_count")
    
    @pytest.mark.asyncio
    async def test_get_cached_result_increments_hit_count(self, cache_manager, mock_redis):
        """Test that hit count is incremented on cache hit"""
        cache_key = "test_cache_key"
        result = {"output": "test result"}
        tool_id = uuid4()
        tool_name = "test_tool"
        
        await cache_manager.store_result(cache_key, result, tool_id, tool_name)
        
        # First retrieval
        cached_result1 = await cache_manager.get_cached_result(cache_key)
        assert cached_result1.hit_count == 1
        
        # Second retrieval
        cached_result2 = await cache_manager.get_cached_result(cache_key)
        assert cached_result2.hit_count == 2


class TestCacheInvalidation:
    """Test cache invalidation (Requirement 10.4)"""
    
    @pytest.mark.asyncio
    async def test_invalidate_tool_cache(self, cache_manager, mock_redis):
        """Test invalidating all cache entries for a tool"""
        tool_id = uuid4()
        tool_name = "test_tool"
        
        # Store multiple results for the same tool
        for i in range(3):
            cache_key = f"cache_key_{i}"
            result = {"output": f"result {i}"}
            await cache_manager.store_result(cache_key, result, tool_id, tool_name)
        
        # Store a result for a different tool
        other_tool_id = uuid4()
        other_cache_key = "other_cache_key"
        await cache_manager.store_result(
            other_cache_key,
            {"output": "other result"},
            other_tool_id,
            "other_tool"
        )
        
        # Invalidate cache for the first tool
        invalidated_count = await cache_manager.invalidate_tool_cache(tool_id)
        
        assert invalidated_count == 3
        
        # Verify the other tool's cache is still present
        other_result = await cache_manager.get_cached_result(other_cache_key)
        assert other_result is not None
    
    @pytest.mark.asyncio
    async def test_invalidate_all(self, cache_manager, mock_redis):
        """Test invalidating all cache entries"""
        # Store multiple results
        for i in range(5):
            cache_key = f"cache_key_{i}"
            result = {"output": f"result {i}"}
            tool_id = uuid4()
            await cache_manager.store_result(cache_key, result, tool_id, "test_tool")
        
        # Invalidate all
        invalidated_count = await cache_manager.invalidate_all()
        
        assert invalidated_count == 5
        
        # Verify all caches are cleared
        for i in range(5):
            cache_key = f"cache_key_{i}"
            cached_result = await cache_manager.get_cached_result(cache_key)
            assert cached_result is None


class TestLRUEviction:
    """Test LRU eviction policy (Requirement 10.5)"""
    
    @pytest.mark.asyncio
    async def test_lru_eviction_when_at_capacity(self, cache_manager, mock_redis):
        """Test that LRU entry is evicted when cache is at capacity"""
        # Set a small cache limit for testing
        original_limit = cache_manager.MAX_CACHE_SIZE
        cache_manager.MAX_CACHE_SIZE = 3
        
        try:
            # Fill cache to capacity
            for i in range(3):
                cache_key = f"cache_key_{i}"
                result = {"output": f"result {i}"}
                tool_id = uuid4()
                await cache_manager.store_result(cache_key, result, tool_id, "test_tool")
                # Small delay to ensure different timestamps
                await asyncio.sleep(0.01)
            
            # Access the second entry to make it more recently used
            await cache_manager.get_cached_result("cache_key_1")
            
            # Add a new entry (should evict the least recently used)
            new_cache_key = "new_cache_key"
            await cache_manager.store_result(
                new_cache_key,
                {"output": "new result"},
                uuid4(),
                "test_tool"
            )
            
            # Verify the first entry (least recently used) was evicted
            first_result = await cache_manager.get_cached_result("cache_key_0")
            assert first_result is None
            
            # Verify the new entry exists
            new_result = await cache_manager.get_cached_result(new_cache_key)
            assert new_result is not None
            
        finally:
            cache_manager.MAX_CACHE_SIZE = original_limit


class TestCacheStatistics:
    """Test cache statistics"""
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, cache_manager, mock_redis):
        """Test retrieving cache statistics"""
        # Store some results
        for i in range(3):
            cache_key = f"cache_key_{i}"
            result = {"output": f"result {i}"}
            tool_id = uuid4()
            await cache_manager.store_result(cache_key, result, tool_id, "test_tool")
        
        # Generate some hits and misses
        await cache_manager.get_cached_result("cache_key_0")
        await cache_manager.get_cached_result("cache_key_1")
        await cache_manager.get_cached_result("nonexistent_key")
        
        stats = await cache_manager.get_cache_stats()
        
        assert isinstance(stats, CacheStats)
        assert stats.total_entries == 3
        assert stats.total_hits == 2
        assert stats.total_misses == 1
        assert stats.hit_rate > 0


class TestUtilityMethods:
    """Test utility methods"""
    
    @pytest.mark.asyncio
    async def test_get_cache_entry_count(self, cache_manager, mock_redis):
        """Test getting cache entry count"""
        # Store some results
        for i in range(5):
            cache_key = f"cache_key_{i}"
            result = {"output": f"result {i}"}
            tool_id = uuid4()
            await cache_manager.store_result(cache_key, result, tool_id, "test_tool")
        
        count = await cache_manager.get_cache_entry_count()
        assert count == 5
    
    @pytest.mark.asyncio
    async def test_exists(self, cache_manager, mock_redis):
        """Test checking if cache entry exists"""
        cache_key = "test_cache_key"
        result = {"output": "test result"}
        tool_id = uuid4()
        
        # Before storing
        exists_before = await cache_manager.exists(cache_key)
        assert not exists_before
        
        # After storing
        await cache_manager.store_result(cache_key, result, tool_id, "test_tool")
        exists_after = await cache_manager.exists(cache_key)
        assert exists_after
    
    @pytest.mark.asyncio
    async def test_get_ttl(self, cache_manager, mock_redis):
        """Test getting TTL for cache entry"""
        cache_key = "test_cache_key"
        result = {"output": "test result"}
        tool_id = uuid4()
        ttl = 3600
        
        await cache_manager.store_result(cache_key, result, tool_id, "test_tool", ttl)
        
        retrieved_ttl = await cache_manager.get_ttl(cache_key)
        assert retrieved_ttl == ttl
