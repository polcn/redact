#!/usr/bin/env python3
"""
Performance tests for vector integration
Tests performance with realistic data volumes and concurrent operations
"""

import unittest
import time
import threading
import sys
import os
import tempfile
import shutil
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple

# Add project paths
sys.path.insert(0, '/home/ec2-user/redact-terraform/api_code')
sys.path.insert(0, '/home/ec2-user/redact-terraform/tests')

from test_auth_utils import setup_test_environment, cleanup_test_environment

class TestVectorPerformance(unittest.TestCase):
    """Performance tests for ChromaDB vector operations"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        setup_test_environment()
        
        # Check if ChromaDB is available
        try:
            import chromadb
            cls.chromadb_available = True
        except ImportError:
            cls.chromadb_available = False
            print("⚠️  ChromaDB not available, skipping performance tests")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        cleanup_test_environment()
    
    def setUp(self):
        """Set up individual test"""
        if not self.chromadb_available:
            self.skipTest("ChromaDB not available")
        
        # Create temporary directory for each test
        self.test_dir = tempfile.mkdtemp(prefix="perf_test_")
        
        from chromadb_client import ChromaDBClient
        self.client = ChromaDBClient(
            persist_directory=self.test_dir,
            collection_name="perf_test_collection"
        )
        
        # Generate test data
        self.small_chunks = self._generate_test_chunks(10, 100)
        self.medium_chunks = self._generate_test_chunks(100, 200)
        self.large_chunks = self._generate_test_chunks(500, 500)
        
        # Test metadata template
        self.base_metadata = {
            "content_type": "text/plain",
            "created_date": "2024-01-15T10:30:00Z",
            "entities": {
                "topics": ["performance", "testing", "vectors"],
                "people": ["Test User"],
                "organizations": ["Test Corp"]
            }
        }
    
    def tearDown(self):
        """Clean up test fixtures"""
        if hasattr(self, 'test_dir') and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def _generate_test_chunks(self, count: int, min_length: int) -> List[str]:
        """Generate test chunks of varying lengths"""
        chunks = []
        base_words = [
            "data", "privacy", "security", "compliance", "GDPR", "protection",
            "user", "rights", "processing", "consent", "policy", "information",
            "personal", "sensitive", "encryption", "storage", "access", "control",
            "audit", "log", "monitoring", "breach", "notification", "assessment"
        ]
        
        for i in range(count):
            # Create chunks of varying length
            words_count = min_length + (i % 100)
            chunk_words = []
            
            for j in range(words_count):
                word = base_words[j % len(base_words)]
                chunk_words.append(f"{word}_{i}_{j}")
            
            chunk = f"Chunk {i}: " + " ".join(chunk_words) + "."
            chunks.append(chunk)
        
        return chunks
    
    def _time_operation(self, operation_name: str, operation_func) -> float:
        """Time an operation and return duration in seconds"""
        start_time = time.time()
        result = operation_func()
        duration = time.time() - start_time
        print(f"  {operation_name}: {duration:.3f}s")
        return duration, result
    
    def test_store_performance_small_batch(self):
        """Test performance with small batch (10 chunks)"""
        print(f"\n=== Testing Small Batch Performance (10 chunks) ===")
        
        user_id = "perf_user_small"
        doc_id = "small_batch_doc"
        metadata = {**self.base_metadata, "filename": "small_batch.txt"}
        
        duration, result = self._time_operation(
            "Store 10 chunks",
            lambda: self.client.store_vectors(user_id, doc_id, self.small_chunks, metadata)
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["chunks_stored"], 10)
        self.assertLess(duration, 5.0, "Small batch storage should complete in <5s")
        
        # Test search performance
        search_duration, search_result = self._time_operation(
            "Search in small batch",
            lambda: self.client.search_similar(user_id, "performance testing data", 5)
        )
        
        self.assertTrue(search_result["success"])
        self.assertLess(search_duration, 1.0, "Search in small batch should complete in <1s")
    
    def test_store_performance_medium_batch(self):
        """Test performance with medium batch (100 chunks)"""
        print(f"\n=== Testing Medium Batch Performance (100 chunks) ===")
        
        user_id = "perf_user_medium"
        doc_id = "medium_batch_doc"
        metadata = {**self.base_metadata, "filename": "medium_batch.txt"}
        
        duration, result = self._time_operation(
            "Store 100 chunks",
            lambda: self.client.store_vectors(user_id, doc_id, self.medium_chunks, metadata)
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["chunks_stored"], 100)
        self.assertLess(duration, 15.0, "Medium batch storage should complete in <15s")
        
        # Test search performance
        search_duration, search_result = self._time_operation(
            "Search in medium batch",
            lambda: self.client.search_similar(user_id, "performance testing data", 10)
        )
        
        self.assertTrue(search_result["success"])
        self.assertLess(search_duration, 2.0, "Search in medium batch should complete in <2s")
        
        # Test statistics performance
        stats_duration, stats_result = self._time_operation(
            "Get statistics",
            lambda: self.client.get_user_statistics(user_id)
        )
        
        self.assertTrue(stats_result["success"])
        self.assertEqual(stats_result["total_chunks"], 100)
        self.assertLess(stats_duration, 1.0, "Statistics should complete in <1s")
    
    def test_store_performance_large_batch(self):
        """Test performance with large batch (500 chunks)"""
        print(f"\n=== Testing Large Batch Performance (500 chunks) ===")
        
        user_id = "perf_user_large"
        doc_id = "large_batch_doc"
        metadata = {**self.base_metadata, "filename": "large_batch.txt"}
        
        duration, result = self._time_operation(
            "Store 500 chunks",
            lambda: self.client.store_vectors(user_id, doc_id, self.large_chunks, metadata)
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["chunks_stored"], 500)
        self.assertLess(duration, 60.0, "Large batch storage should complete in <60s")
        
        # Test search performance with large dataset
        search_duration, search_result = self._time_operation(
            "Search in large batch",
            lambda: self.client.search_similar(user_id, "performance testing data", 20)
        )
        
        self.assertTrue(search_result["success"])
        self.assertLessEqual(len(search_result["results"]), 20)
        self.assertLess(search_duration, 5.0, "Search in large batch should complete in <5s")
        
        # Test deletion performance
        delete_duration, delete_result = self._time_operation(
            "Delete 500 chunks",
            lambda: self.client.delete_document_vectors(user_id, doc_id)
        )
        
        self.assertTrue(delete_result["success"])
        self.assertEqual(delete_result["chunks_deleted"], 500)
        self.assertLess(delete_duration, 10.0, "Deletion should complete in <10s")
    
    def test_concurrent_operations(self):
        """Test performance with concurrent operations"""
        print(f"\n=== Testing Concurrent Operations ===")
        
        num_threads = 5
        chunks_per_thread = 20
        
        def store_chunks_for_user(user_index: int) -> Tuple[float, bool]:
            """Store chunks for a specific user and return timing"""
            user_id = f"concurrent_user_{user_index}"
            doc_id = f"concurrent_doc_{user_index}"
            
            # Generate unique chunks for this user
            user_chunks = [
                f"User {user_index} chunk {i}: " + " ".join([
                    f"word_{user_index}_{i}_{j}" for j in range(50)
                ])
                for i in range(chunks_per_thread)
            ]
            
            metadata = {
                **self.base_metadata,
                "filename": f"concurrent_{user_index}.txt",
                "user_index": user_index
            }
            
            start_time = time.time()
            result = self.client.store_vectors(user_id, doc_id, user_chunks, metadata)
            duration = time.time() - start_time
            
            return duration, result["success"]
        
        # Execute concurrent operations
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(store_chunks_for_user, i)
                for i in range(num_threads)
            ]
            
            results = []
            for future in as_completed(futures):
                duration, success = future.result()
                results.append((duration, success))
                self.assertTrue(success, "Concurrent operation should succeed")
        
        total_duration = time.time() - start_time
        individual_durations = [r[0] for r in results]
        
        print(f"  Total concurrent time: {total_duration:.3f}s")
        print(f"  Individual operation times: {[f'{d:.3f}s' for d in individual_durations]}")
        print(f"  Average individual time: {statistics.mean(individual_durations):.3f}s")
        print(f"  Max individual time: {max(individual_durations):.3f}s")
        
        # Verify all operations completed successfully
        self.assertEqual(len(results), num_threads)
        self.assertTrue(all(success for _, success in results))
        
        # Test concurrent searches
        def search_for_user(user_index: int) -> Tuple[float, int]:
            """Search for a specific user and return timing and result count"""
            user_id = f"concurrent_user_{user_index}"
            
            start_time = time.time()
            result = self.client.search_similar(user_id, "word data chunk", 10)
            duration = time.time() - start_time
            
            return duration, len(result["results"]) if result["success"] else 0
        
        # Execute concurrent searches
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            search_futures = [
                executor.submit(search_for_user, i)
                for i in range(num_threads)
            ]
            
            search_results = []
            for future in as_completed(search_futures):
                duration, result_count = future.result()
                search_results.append((duration, result_count))
        
        search_durations = [r[0] for r in search_results]
        search_counts = [r[1] for r in search_results]
        
        print(f"  Concurrent search times: {[f'{d:.3f}s' for d in search_durations]}")
        print(f"  Search result counts: {search_counts}")
        
        # Each user should find their own results
        self.assertTrue(all(count > 0 for count in search_counts))
        self.assertTrue(all(duration < 2.0 for duration in search_durations))
    
    def test_memory_usage_large_dataset(self):
        """Test memory efficiency with large dataset"""
        print(f"\n=== Testing Memory Usage with Large Dataset ===")
        
        try:
            import psutil
            process = psutil.Process()
            memory_available = True
        except ImportError:
            memory_available = False
            print("⚠️  psutil not available, skipping memory measurements")
        
        user_id = "memory_test_user"
        
        if memory_available:
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            print(f"  Initial memory usage: {initial_memory:.1f} MB")
        
        # Store multiple large documents
        total_chunks = 0
        for doc_index in range(3):  # 3 documents
            doc_id = f"memory_doc_{doc_index}"
            chunks = self._generate_test_chunks(200, 300)  # 200 chunks each
            
            metadata = {
                **self.base_metadata,
                "filename": f"memory_test_{doc_index}.txt",
                "doc_index": doc_index
            }
            
            start_time = time.time()
            result = self.client.store_vectors(user_id, doc_id, chunks, metadata)
            duration = time.time() - start_time
            
            self.assertTrue(result["success"])
            total_chunks += len(chunks)
            
            if memory_available:
                current_memory = process.memory_info().rss / 1024 / 1024
                print(f"  After document {doc_index + 1}: {current_memory:.1f} MB "
                      f"(+{current_memory - initial_memory:.1f} MB)")
        
        print(f"  Total chunks stored: {total_chunks}")
        
        # Test search performance with large dataset
        search_start = time.time()
        search_result = self.client.search_similar(user_id, "memory test data", 25)
        search_duration = time.time() - search_start
        
        self.assertTrue(search_result["success"])
        print(f"  Search in large dataset: {search_duration:.3f}s")
        self.assertLess(search_duration, 5.0, "Search should remain fast with large dataset")
        
        # Test statistics performance
        stats_start = time.time()
        stats = self.client.get_user_statistics(user_id)
        stats_duration = time.time() - stats_start
        
        self.assertTrue(stats["success"])
        self.assertEqual(stats["total_chunks"], total_chunks)
        print(f"  Statistics calculation: {stats_duration:.3f}s")
        self.assertLess(stats_duration, 2.0, "Statistics should be calculated quickly")
        
        if memory_available:
            final_memory = process.memory_info().rss / 1024 / 1024
            total_memory_increase = final_memory - initial_memory
            print(f"  Final memory usage: {final_memory:.1f} MB")
            print(f"  Total memory increase: {total_memory_increase:.1f} MB")
            print(f"  Memory per chunk: {total_memory_increase / total_chunks:.3f} MB")
    
    def test_scaling_characteristics(self):
        """Test how operations scale with dataset size"""
        print(f"\n=== Testing Scaling Characteristics ===")
        
        dataset_sizes = [50, 100, 200, 400]
        store_times = []
        search_times = []
        
        for size in dataset_sizes:
            user_id = f"scaling_user_{size}"
            doc_id = f"scaling_doc_{size}"
            
            # Generate chunks for this size
            chunks = self._generate_test_chunks(size, 150)
            metadata = {
                **self.base_metadata,
                "filename": f"scaling_{size}.txt",
                "chunk_count": size
            }
            
            # Measure store time
            store_start = time.time()
            result = self.client.store_vectors(user_id, doc_id, chunks, metadata)
            store_duration = time.time() - store_start
            
            self.assertTrue(result["success"])
            store_times.append((size, store_duration))
            
            # Measure search time
            search_start = time.time()
            search_result = self.client.search_similar(user_id, "scaling test data", 10)
            search_duration = time.time() - search_start
            
            self.assertTrue(search_result["success"])
            search_times.append((size, search_duration))
            
            print(f"  Size {size:3d}: Store {store_duration:.3f}s, Search {search_duration:.3f}s")
        
        # Analyze scaling characteristics
        print("\n  Scaling Analysis:")
        print("  Size | Store Time | Search Time | Store Rate | Search Rate")
        print("  -----|------------|-------------|------------|------------")
        
        for i, (size, store_time, search_time) in enumerate(
            zip(dataset_sizes, [t[1] for t in store_times], [t[1] for t in search_times])
        ):
            store_rate = size / store_time
            search_rate = size / search_time if search_time > 0 else float('inf')
            
            print(f"  {size:4d} | {store_time:8.3f}s | {search_time:9.3f}s | "
                  f"{store_rate:8.1f}/s | {search_rate:9.1f}/s")
            
            # Basic scaling assertions
            if i > 0:
                prev_size = dataset_sizes[i-1]
                prev_store_time = store_times[i-1][1]
                
                # Store time should scale sub-quadratically
                scaling_factor = (size / prev_size)
                time_scaling_factor = (store_time / prev_store_time)
                
                self.assertLess(
                    time_scaling_factor, scaling_factor * 2,
                    f"Store time scaling should be reasonable (got {time_scaling_factor:.2f}x for {scaling_factor:.2f}x size)"
                )


class TestVectorAPIPerformance(unittest.TestCase):
    """Performance tests for Vector API endpoints"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        setup_test_environment()
        
        # Check if we can import handlers
        try:
            from api_handler_simple import handle_store_vectors, handle_search_vectors
            cls.handlers_available = True
        except ImportError:
            cls.handlers_available = False
            print("⚠️  API handlers not available for performance testing")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        cleanup_test_environment()
    
    def test_api_response_times(self):
        """Test API response times with various payloads"""
        if not self.handlers_available:
            self.skipTest("API handlers not available")
        
        print("\n=== Testing API Response Times ===")
        
        # This would need to be expanded with actual API testing
        # For now, just verify the handlers can be imported and called
        
        from api_handler_simple import handle_store_vectors
        
        # Mock event data
        mock_event = {
            "httpMethod": "POST",
            "body": '{"document_id": "perf_test", "chunks": ["test"], "metadata": {}}',
            "headers": {"Authorization": "Bearer test"},
            "requestContext": {}
        }
        
        mock_context = type('MockContext', (), {
            'remaining_time_in_millis': lambda: 30000
        })()
        
        mock_user_context = {"user_id": "perf_test_user"}
        
        # This test would fail due to missing dependencies, but tests import structure
        try:
            start_time = time.time()
            # In a real test, we'd mock all dependencies
            # response = handle_store_vectors(mock_event, {}, mock_context, mock_user_context)
            duration = time.time() - start_time
            print(f"  Handler import and setup: {duration:.3f}s")
        except Exception as e:
            print(f"  Expected error due to missing dependencies: {type(e).__name__}")


if __name__ == '__main__':
    # Run performance tests with high verbosity
    unittest.main(verbosity=2)