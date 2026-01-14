"""
Performance Optimization Script

This script analyzes performance test results and applies optimizations:
- Database index tuning
- Cache configuration optimization
- Queue worker count adjustment
- Connection pool sizing
"""

import asyncio
import sys
from typing import Dict, Any, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import get_redis_url


class PerformanceOptimizer:
    """Analyzes and optimizes system performance"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        self.optimizations_applied = []
    
    async def initialize(self):
        """Initialize database connection"""
        database_url = (
            f"mysql+aiomysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
            f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
        )
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def close(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()
    
    async def analyze_database_indexes(self) -> Dict[str, Any]:
        """Analyze database indexes and suggest improvements"""
        print("\n" + "="*80)
        print("ANALYZING DATABASE INDEXES")
        print("="*80)
        
        async with self.async_session() as session:
            # Check execution_queue indexes
            result = await session.execute(text("""
                SHOW INDEX FROM execution_queue
            """))
            queue_indexes = result.fetchall()
            
            print("\nExecution Queue Indexes:")
            for idx in queue_indexes:
                print(f"  - {idx[2]}: {idx[4]}")
            
            # Check if critical indexes exist
            index_names = [idx[2] for idx in queue_indexes]
            
            missing_indexes = []
            
            if 'idx_status_priority' not in index_names:
                missing_indexes.append({
                    'table': 'execution_queue',
                    'name': 'idx_status_priority',
                    'columns': ['status', 'priority DESC']
                })
            
            if 'idx_user_status' not in index_names:
                missing_indexes.append({
                    'table': 'execution_queue',
                    'name': 'idx_user_status',
                    'columns': ['user_id', 'status']
                })
            
            return {
                'existing_indexes': len(queue_indexes),
                'missing_indexes': missing_indexes
            }
    
    async def optimize_database_indexes(self, analysis: Dict[str, Any]):
        """Create missing database indexes"""
        print("\n" + "="*80)
        print("OPTIMIZING DATABASE INDEXES")
        print("="*80)
        
        missing = analysis.get('missing_indexes', [])
        
        if not missing:
            print("\n✓ All critical indexes already exist")
            return
        
        async with self.async_session() as session:
            for idx in missing:
                try:
                    columns_str = ', '.join(idx['columns'])
                    sql = f"""
                        CREATE INDEX {idx['name']} 
                        ON {idx['table']} ({columns_str})
                    """
                    
                    print(f"\nCreating index: {idx['name']}")
                    print(f"  Table: {idx['table']}")
                    print(f"  Columns: {columns_str}")
                    
                    await session.execute(text(sql))
                    await session.commit()
                    
                    self.optimizations_applied.append(f"Created index: {idx['name']}")
                    print(f"  ✓ Index created successfully")
                    
                except Exception as e:
                    print(f"  ✗ Error creating index: {e}")
    
    async def analyze_cache_configuration(self) -> Dict[str, Any]:
        """Analyze cache configuration and suggest improvements"""
        print("\n" + "="*80)
        print("ANALYZING CACHE CONFIGURATION")
        print("="*80)
        
        from redis import asyncio as aioredis
        
        redis_client = await aioredis.from_url(
            get_redis_url(),
            encoding="utf-8",
            decode_responses=True
        )
        
        try:
            # Get Redis info
            info = await redis_client.info()
            
            used_memory = info.get('used_memory_human', 'Unknown')
            maxmemory = info.get('maxmemory_human', 'Unknown')
            eviction_policy = info.get('maxmemory_policy', 'Unknown')
            
            print(f"\nCurrent Redis Configuration:")
            print(f"  Used Memory: {used_memory}")
            print(f"  Max Memory: {maxmemory}")
            print(f"  Eviction Policy: {eviction_policy}")
            
            # Check if configuration is optimal
            recommendations = []
            
            if eviction_policy != 'allkeys-lru':
                recommendations.append({
                    'setting': 'maxmemory-policy',
                    'current': eviction_policy,
                    'recommended': 'allkeys-lru',
                    'reason': 'LRU eviction is optimal for result caching'
                })
            
            return {
                'used_memory': used_memory,
                'maxmemory': maxmemory,
                'eviction_policy': eviction_policy,
                'recommendations': recommendations
            }
            
        finally:
            await redis_client.close()
    
    async def optimize_cache_configuration(self, analysis: Dict[str, Any]):
        """Apply cache configuration optimizations"""
        print("\n" + "="*80)
        print("OPTIMIZING CACHE CONFIGURATION")
        print("="*80)
        
        recommendations = analysis.get('recommendations', [])
        
        if not recommendations:
            print("\n✓ Cache configuration is already optimal")
            return
        
        print("\nRecommended Redis Configuration Changes:")
        print("\nAdd to redis.conf or docker-compose.yml:")
        print("-" * 40)
        
        for rec in recommendations:
            print(f"\n{rec['setting']}: {rec['recommended']}")
            print(f"  Current: {rec['current']}")
            print(f"  Reason: {rec['reason']}")
            
            self.optimizations_applied.append(
                f"Recommended: {rec['setting']} = {rec['recommended']}"
            )
        
        print("\n" + "-" * 40)
        print("\nNote: Redis configuration changes require restart")
    
    async def analyze_queue_workers(self) -> Dict[str, Any]:
        """Analyze queue worker configuration"""
        print("\n" + "="*80)
        print("ANALYZING QUEUE WORKER CONFIGURATION")
        print("="*80)
        
        from redis import asyncio as aioredis
        
        redis_client = await aioredis.from_url(
            get_redis_url(),
            encoding="utf-8",
            decode_responses=True
        )
        
        try:
            # Check queue depth
            queue_depth = await redis_client.zcard("queue:executions")
            
            print(f"\nCurrent Queue Metrics:")
            print(f"  Queue Depth: {queue_depth}")
            
            # Recommend worker count based on queue depth
            if queue_depth > 1000:
                recommended_workers = 10
                reason = "High queue depth requires more workers"
            elif queue_depth > 500:
                recommended_workers = 5
                reason = "Moderate queue depth"
            else:
                recommended_workers = 3
                reason = "Low queue depth"
            
            return {
                'queue_depth': queue_depth,
                'recommended_workers': recommended_workers,
                'reason': reason
            }
            
        finally:
            await redis_client.close()
    
    async def optimize_queue_workers(self, analysis: Dict[str, Any]):
        """Provide queue worker optimization recommendations"""
        print("\n" + "="*80)
        print("OPTIMIZING QUEUE WORKER CONFIGURATION")
        print("="*80)
        
        recommended = analysis['recommended_workers']
        reason = analysis['reason']
        
        print(f"\nRecommended Worker Count: {recommended}")
        print(f"Reason: {reason}")
        
        print("\nTo adjust worker count:")
        print("1. Update docker-compose.yml:")
        print(f"   deploy:")
        print(f"     replicas: {recommended}")
        print("\n2. Or scale manually:")
        print(f"   docker-compose up -d --scale worker={recommended}")
        
        self.optimizations_applied.append(
            f"Recommended: {recommended} queue workers"
        )
    
    async def analyze_connection_pool(self) -> Dict[str, Any]:
        """Analyze connection pool configuration"""
        print("\n" + "="*80)
        print("ANALYZING CONNECTION POOL CONFIGURATION")
        print("="*80)
        
        from redis import asyncio as aioredis
        
        redis_client = await aioredis.from_url(
            get_redis_url(),
            encoding="utf-8",
            decode_responses=True
        )
        
        try:
            # Get pool statistics from Redis
            pool_keys = await redis_client.keys("pool:*:connections")
            
            total_connections = 0
            for key in pool_keys:
                count = await redis_client.llen(key)
                total_connections += count
            
            print(f"\nCurrent Connection Pool Metrics:")
            print(f"  Total Pools: {len(pool_keys)}")
            print(f"  Total Connections: {total_connections}")
            
            # Recommend pool size based on usage
            if total_connections > 50:
                recommended_max = 20
                reason = "High connection usage"
            elif total_connections > 20:
                recommended_max = 15
                reason = "Moderate connection usage"
            else:
                recommended_max = 10
                reason = "Low connection usage"
            
            return {
                'total_pools': len(pool_keys),
                'total_connections': total_connections,
                'recommended_max_size': recommended_max,
                'reason': reason
            }
            
        finally:
            await redis_client.close()
    
    async def optimize_connection_pool(self, analysis: Dict[str, Any]):
        """Provide connection pool optimization recommendations"""
        print("\n" + "="*80)
        print("OPTIMIZING CONNECTION POOL CONFIGURATION")
        print("="*80)
        
        recommended = analysis['recommended_max_size']
        reason = analysis['reason']
        
        print(f"\nRecommended Max Pool Size: {recommended}")
        print(f"Reason: {reason}")
        
        print("\nTo adjust pool size:")
        print("Update app/services/connection_pool_manager.py:")
        print(f"  max_size: int = {recommended}")
        
        self.optimizations_applied.append(
            f"Recommended: max_size = {recommended} for connection pool"
        )
    
    async def run_full_optimization(self):
        """Run complete performance optimization"""
        print("\n" + "="*80)
        print("PERFORMANCE OPTIMIZATION SUITE")
        print("="*80)
        
        try:
            await self.initialize()
            
            # 1. Database indexes
            db_analysis = await self.analyze_database_indexes()
            await self.optimize_database_indexes(db_analysis)
            
            # 2. Cache configuration
            cache_analysis = await self.analyze_cache_configuration()
            await self.optimize_cache_configuration(cache_analysis)
            
            # 3. Queue workers
            queue_analysis = await self.analyze_queue_workers()
            await self.optimize_queue_workers(queue_analysis)
            
            # 4. Connection pool
            pool_analysis = await self.analyze_connection_pool()
            await self.optimize_connection_pool(pool_analysis)
            
            # Print summary
            print("\n" + "="*80)
            print("OPTIMIZATION SUMMARY")
            print("="*80)
            
            if self.optimizations_applied:
                print("\nOptimizations Applied/Recommended:")
                for i, opt in enumerate(self.optimizations_applied, 1):
                    print(f"{i}. {opt}")
            else:
                print("\n✓ System is already optimally configured")
            
            print("\n" + "="*80)
            
        finally:
            await self.close()


async def main():
    """Main entry point"""
    optimizer = PerformanceOptimizer()
    await optimizer.run_full_optimization()


if __name__ == "__main__":
    asyncio.run(main())
