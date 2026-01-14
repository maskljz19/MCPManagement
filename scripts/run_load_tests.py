"""
Load Testing Script for MCP Execution Enhancements

Runs comprehensive load tests and generates a report.
"""

import asyncio
import time
import statistics
from uuid import uuid4
import random
from typing import Dict, Any, List
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.services.execution_queue_manager import ExecutionQueueManager
from app.services.connection_pool_manager import ConnectionPoolManager
from app.services.rate_limiter import RateLimiter
from app.services.resource_quota_manager import ResourceQuotaManager
from app.core.config import settings


class LoadTestRunner:
    """Runs load tests and collects results"""
    
    def __init__(self):
        self.results = {}
        self.redis_client = None
        self.db_session = None
        
    async def setup(self):
        """Setup test dependencies"""
        print("Setting up test environment...")
        
        # Setup Redis
        self.redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=15,  # Use test database
            decode_responses=True
        )
        
        # Test Redis connection
        await self.redis_client.ping()
        await self.redis_client.flushdb()
        
        # Setup Database
        database_url = (
            f"mysql+aiomysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
            f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
        )
        engine = create_async_engine(database_url, echo=False)
        async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session_factory() as session:
            self.db_session = session
            
        print("✓ Setup complete\n")
        
    async def cleanup(self):
        """Cleanup test resources"""
        if self.redis_client:
            await self.redis_client.flushdb()
            await self.redis_client.close()
    
    async def test_concurrent_execution_limits(self):
        """Test concurrent execution limits"""
        print("="*80)
        print("TEST 1: Concurrent Execution Limits")
        print("="*80)
        
        queue_service = ExecutionQueueManager(self.redis_client)
        
        num_concurrent = 100
        print(f"Testing {num_concurrent} concurrent executions...")
        
        # Enqueue
        start_time = time.time()
        tasks = []
        
        for i in range(num_concurrent):
            task = queue_service.enqueue(
                execution_id=str(uuid4()),
                tool_id=str(uuid4()),
                user_id=str(uuid4()),
                tool_name=f"test_tool_{i}",
                arguments={'index': i},
                options={},
                priority=random.randint(1, 10)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        enqueue_time = time.time() - start_time
        
        # Dequeue
        dequeue_start = time.time()
        dequeue_tasks = [queue_service.dequeue() for _ in range(num_concurrent)]
        dequeued = await asyncio.gather(*dequeue_tasks)
        successful = sum(1 for e in dequeued if e is not None)
        dequeue_time = time.time() - dequeue_start
        
        # Calculate metrics
        total_time = enqueue_time + dequeue_time
        throughput = (num_concurrent * 2) / total_time
        success_rate = (successful / num_concurrent) * 100
        
        print(f"\nResults:")
        print(f"  Enqueue time: {enqueue_time:.2f}s")
        print(f"  Dequeue time: {dequeue_time:.2f}s")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.2f} ops/sec")
        print(f"  Success rate: {success_rate:.2f}%")
        
        self.results['concurrent_execution'] = {
            'throughput': throughput,
            'success_rate': success_rate,
            'passed': throughput >= 50 and success_rate >= 95
        }
        
        print(f"\n{'✓ PASS' if self.results['concurrent_execution']['passed'] else '✗ FAIL'}\n")
    
    async def test_queue_capacity(self):
        """Test queue capacity handling"""
        print("="*80)
        print("TEST 2: Queue Capacity Handling")
        print("="*80)
        
        queue_service = ExecutionQueueManager(self.redis_client)
        
        capacity = 500
        print(f"Filling queue with {capacity} items...")
        
        # Fill queue
        fill_start = time.time()
        for i in range(capacity):
            await queue_service.enqueue(
                execution_id=str(uuid4()),
                tool_id=str(uuid4()),
                user_id=str(uuid4()),
                tool_name="capacity_test",
                arguments={'index': i},
                options={},
                priority=5
            )
        fill_time = time.time() - fill_start
        
        # Process items
        process_count = 100
        process_start = time.time()
        processed = 0
        
        for _ in range(process_count):
            if await queue_service.dequeue():
                processed += 1
        
        process_time = time.time() - process_start
        throughput = processed / process_time if process_time > 0 else 0
        
        print(f"\nResults:")
        print(f"  Fill time: {fill_time:.2f}s")
        print(f"  Process time: {process_time:.2f}s")
        print(f"  Processing throughput: {throughput:.2f} items/sec")
        
        self.results['queue_capacity'] = {
            'throughput': throughput,
            'passed': throughput >= 50
        }
        
        # Cleanup
        for _ in range(capacity - process_count):
            await queue_service.dequeue()
        
        print(f"\n{'✓ PASS' if self.results['queue_capacity']['passed'] else '✗ FAIL'}\n")
    
    async def test_connection_pool(self):
        """Test connection pool under stress"""
        print("="*80)
        print("TEST 3: Connection Pool Stress")
        print("="*80)
        
        pool_service = ConnectionPoolManager(self.redis_client)
        
        num_requests = 100
        tool_ids = [str(uuid4()) for _ in range(10)]
        
        print(f"Testing {num_requests} concurrent connection requests...")
        
        connection_times = []
        successful = 0
        failed = 0
        
        async def get_and_release(tool_id):
            nonlocal successful, failed
            try:
                start = time.time()
                conn = await pool_service.get_connection(tool_id)
                conn_time = (time.time() - start) * 1000
                connection_times.append(conn_time)
                
                await asyncio.sleep(0.01)
                await pool_service.release_connection(conn)
                successful += 1
            except Exception:
                failed += 1
        
        start_time = time.time()
        tasks = [get_and_release(random.choice(tool_ids)) for _ in range(num_requests)]
        await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        avg_time = statistics.mean(connection_times) if connection_times else 0
        p95_time = statistics.quantiles(connection_times, n=20)[18] if len(connection_times) >= 20 else avg_time
        success_rate = (successful / num_requests) * 100
        
        print(f"\nResults:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Successful: {successful}/{num_requests}")
        print(f"  Success rate: {success_rate:.2f}%")
        print(f"  Avg connection time: {avg_time:.2f}ms")
        print(f"  P95 connection time: {p95_time:.2f}ms")
        
        self.results['connection_pool'] = {
            'success_rate': success_rate,
            'p95_time': p95_time,
            'passed': success_rate >= 80 and p95_time <= 200
        }
        
        print(f"\n{'✓ PASS' if self.results['connection_pool']['passed'] else '✗ FAIL'}\n")
    
    async def test_rate_limiter(self):
        """Test rate limiter accuracy"""
        print("="*80)
        print("TEST 4: Rate Limiter Accuracy")
        print("="*80)
        
        rate_limiter = RateLimiter(self.redis_client)
        
        user_id = str(uuid4())
        resource = "executions"
        limit = 100
        
        print(f"Testing rate limiter with limit of {limit} requests...")
        
        # Test 1: Within limit
        allowed = 0
        for _ in range(limit):
            result = await rate_limiter.check_rate_limit(user_id, resource)
            if result.allowed:
                await rate_limiter.consume_quota(user_id, resource, 1)
                allowed += 1
        
        accuracy1 = (allowed / limit) * 100
        
        # Test 2: Over limit
        denied = 0
        for _ in range(limit):
            result = await rate_limiter.check_rate_limit(user_id, resource)
            if not result.allowed:
                denied += 1
        
        accuracy2 = (denied / limit) * 100
        
        # Test 3: Concurrent
        await rate_limiter.reset_rate_limit(user_id, resource)
        concurrent_allowed = 0
        
        async def check():
            nonlocal concurrent_allowed
            result = await rate_limiter.check_rate_limit(user_id, resource)
            if result.allowed:
                await rate_limiter.consume_quota(user_id, resource, 1)
                concurrent_allowed += 1
        
        await asyncio.gather(*[check() for _ in range(limit)])
        accuracy3 = (concurrent_allowed / limit) * 100
        
        avg_accuracy = (accuracy1 + accuracy2 + accuracy3) / 3
        
        print(f"\nResults:")
        print(f"  Test 1 (within limit): {accuracy1:.2f}%")
        print(f"  Test 2 (over limit): {accuracy2:.2f}%")
        print(f"  Test 3 (concurrent): {accuracy3:.2f}%")
        print(f"  Average accuracy: {avg_accuracy:.2f}%")
        
        self.results['rate_limiter'] = {
            'accuracy': avg_accuracy,
            'passed': avg_accuracy >= 90
        }
        
        print(f"\n{'✓ PASS' if self.results['rate_limiter']['passed'] else '✗ FAIL'}\n")
    
    async def test_resource_quota(self):
        """Test resource quota enforcement"""
        print("="*80)
        print("TEST 5: Resource Quota Enforcement")
        print("="*80)
        
        quota_manager = ResourceQuotaManager(self.redis_client, self.db_session)
        
        user_id = str(uuid4())
        max_concurrent = 20
        
        print(f"Testing resource quota with max {max_concurrent} concurrent executions...")
        
        allocations = []
        successful = 0
        failed = 0
        
        for i in range(25):
            execution_id = str(uuid4())
            requirements = {
                'cpu_cores': 0.5,
                'memory_mb': 512,
                'concurrent_executions': 1
            }
            
            quota_check = await quota_manager.check_quota(user_id, requirements)
            if quota_check.allowed:
                if await quota_manager.allocate_resources(execution_id, user_id, requirements):
                    allocations.append(execution_id)
                    successful += 1
            else:
                failed += 1
        
        enforcement_accuracy = min(100, (min(successful, max_concurrent) / max_concurrent) * 100)
        
        print(f"\nResults:")
        print(f"  Successful allocations: {successful}")
        print(f"  Failed allocations: {failed}")
        print(f"  Enforcement accuracy: {enforcement_accuracy:.2f}%")
        
        # Cleanup
        for execution_id in allocations:
            await quota_manager.release_resources(execution_id)
        
        self.results['resource_quota'] = {
            'accuracy': enforcement_accuracy,
            'passed': enforcement_accuracy >= 80
        }
        
        print(f"\n{'✓ PASS' if self.results['resource_quota']['passed'] else '✗ FAIL'}\n")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("LOAD TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r['passed'])
        
        for test_name, result in self.results.items():
            status = "✓ PASS" if result['passed'] else "✗ FAIL"
            print(f"\n{test_name}: {status}")
            for key, value in result.items():
                if key != 'passed':
                    print(f"  {key}: {value:.2f}")
        
        print(f"\n{'='*80}")
        print(f"Total: {passed_tests}/{total_tests} tests passed")
        print(f"{'='*80}\n")
        
        return passed_tests == total_tests


async def main():
    """Run all load tests"""
    runner = LoadTestRunner()
    
    try:
        await runner.setup()
        
        # Run tests
        await runner.test_concurrent_execution_limits()
        await runner.test_queue_capacity()
        await runner.test_connection_pool()
        await runner.test_rate_limiter()
        await runner.test_resource_quota()
        
        # Print summary
        all_passed = runner.print_summary()
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"\n✗ Error running load tests: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
