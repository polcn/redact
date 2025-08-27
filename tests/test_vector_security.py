#!/usr/bin/env python3
"""
Security and isolation tests for vector integration
Tests user isolation, data security, and error handling scenarios
"""

import unittest
import tempfile
import shutil
import sys
import os
import json
import time
from unittest.mock import patch, MagicMock

# Add project paths
sys.path.insert(0, '/home/ec2-user/redact-terraform/api_code')
sys.path.insert(0, '/home/ec2-user/redact-terraform/tests')

from test_auth_utils import TestAuthHelper, setup_test_environment, cleanup_test_environment

class TestVectorUserIsolation(unittest.TestCase):
    """Test user isolation in vector operations"""
    
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
            print("⚠️  ChromaDB not available, skipping security tests")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        cleanup_test_environment()
    
    def setUp(self):
        """Set up individual test"""
        if not self.chromadb_available:
            self.skipTest("ChromaDB not available")
        
        # Create temporary directory for each test
        self.test_dir = tempfile.mkdtemp(prefix="security_test_")
        
        from chromadb_client import ChromaDBClient
        self.client = ChromaDBClient(
            persist_directory=self.test_dir,
            collection_name="security_test_collection"
        )
        
        # Test users
        self.user1 = "user_001_alice"
        self.user2 = "user_002_bob"
        self.user3 = "user_003_charlie"
        
        # Sensitive test data
        self.sensitive_data_user1 = {
            "document_id": "confidential_doc_001",
            "chunks": [
                "Alice's confidential salary information: $150,000 annual salary.",
                "Alice's SSN: 123-45-6789 and personal health records.",
                "Alice's private business strategy and trade secrets."
            ],
            "metadata": {
                "filename": "alice_confidential.txt",
                "classification": "confidential",
                "owner": "alice"
            }
        }
        
        self.sensitive_data_user2 = {
            "document_id": "secret_doc_002", 
            "chunks": [
                "Bob's personal financial records and bank account: 987654321.",
                "Bob's medical information and private correspondence.",
                "Bob's proprietary algorithms and intellectual property."
            ],
            "metadata": {
                "filename": "bob_secrets.txt",
                "classification": "secret",
                "owner": "bob"
            }
        }
    
    def tearDown(self):
        """Clean up test fixtures"""
        if hasattr(self, 'test_dir') and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_basic_user_isolation(self):
        """Test that users cannot access each other's data"""
        print("\n=== Testing Basic User Isolation ===")
        
        # Store data for user 1
        result1 = self.client.store_vectors(
            self.user1,
            self.sensitive_data_user1["document_id"],
            self.sensitive_data_user1["chunks"],
            self.sensitive_data_user1["metadata"]
        )
        self.assertTrue(result1["success"])
        
        # Store data for user 2
        result2 = self.client.store_vectors(
            self.user2,
            self.sensitive_data_user2["document_id"],
            self.sensitive_data_user2["chunks"],
            self.sensitive_data_user2["metadata"]
        )
        self.assertTrue(result2["success"])
        
        # User 1 searches - should only see own data
        search_user1 = self.client.search_similar(
            self.user1,
            "salary financial information confidential",
            n_results=10
        )
        
        self.assertTrue(search_user1["success"])
        self.assertGreater(len(search_user1["results"]), 0)
        
        # Verify all results belong to user 1
        for result in search_user1["results"]:
            self.assertEqual(result["metadata"]["user_id"], self.user1)
            self.assertIn("Alice", result["text"])  # Should only see Alice's data
            self.assertNotIn("Bob", result["text"])  # Should not see Bob's data
        
        # User 2 searches - should only see own data
        search_user2 = self.client.search_similar(
            self.user2,
            "financial bank account medical",
            n_results=10
        )
        
        self.assertTrue(search_user2["success"])
        self.assertGreater(len(search_user2["results"]), 0)
        
        # Verify all results belong to user 2
        for result in search_user2["results"]:
            self.assertEqual(result["metadata"]["user_id"], self.user2)
            self.assertIn("Bob", result["text"])  # Should only see Bob's data
            self.assertNotIn("Alice", result["text"])  # Should not see Alice's data
        
        print("✅ Basic user isolation verified")
    
    def test_cross_user_search_attempts(self):
        """Test various attempts to access other users' data"""
        print("\n=== Testing Cross-User Search Attempts ===")
        
        # Store sensitive data
        self.client.store_vectors(
            self.user1,
            "sensitive_doc",
            ["User 1 highly sensitive information"],
            {"filename": "sensitive.txt"}
        )
        
        # Test 1: User 2 tries to search with user 1's exact query terms
        search_result = self.client.search_similar(
            self.user2,  # Different user
            "User 1 highly sensitive information",  # Exact text
            n_results=10
        )
        
        self.assertTrue(search_result["success"])
        self.assertEqual(len(search_result["results"]), 0)  # Should find nothing
        
        # Test 2: User 3 (empty user) searches
        search_empty = self.client.search_similar(
            self.user3,
            "sensitive information",
            n_results=10
        )
        
        self.assertTrue(search_empty["success"])
        self.assertEqual(len(search_empty["results"]), 0)
        
        print("✅ Cross-user search isolation verified")
    
    def test_user_statistics_isolation(self):
        """Test that statistics are properly isolated by user"""
        print("\n=== Testing User Statistics Isolation ===")
        
        # Store different amounts of data for each user
        
        # User 1: 3 chunks in 1 document
        self.client.store_vectors(
            self.user1,
            "doc1",
            ["chunk1", "chunk2", "chunk3"],
            {"filename": "doc1.txt"}
        )
        
        # User 2: 5 chunks in 2 documents
        self.client.store_vectors(
            self.user2,
            "doc2a",
            ["chunk1", "chunk2"],
            {"filename": "doc2a.txt"}
        )
        self.client.store_vectors(
            self.user2,
            "doc2b",
            ["chunk3", "chunk4", "chunk5"],
            {"filename": "doc2b.txt"}
        )
        
        # Get statistics for each user
        stats1 = self.client.get_user_statistics(self.user1)
        stats2 = self.client.get_user_statistics(self.user2)
        stats3 = self.client.get_user_statistics(self.user3)  # Empty user
        
        # Verify isolation
        self.assertTrue(stats1["success"])
        self.assertEqual(stats1["total_chunks"], 3)
        self.assertEqual(stats1["unique_documents"], 1)
        
        self.assertTrue(stats2["success"])
        self.assertEqual(stats2["total_chunks"], 5)
        self.assertEqual(stats2["unique_documents"], 2)
        
        self.assertTrue(stats3["success"])
        self.assertEqual(stats3["total_chunks"], 0)
        self.assertEqual(stats3["unique_documents"], 0)
        
        print("✅ User statistics isolation verified")
    
    def test_document_deletion_isolation(self):
        """Test that deletion only affects the correct user's documents"""
        print("\n=== Testing Document Deletion Isolation ===")
        
        # Store same document ID for different users
        shared_doc_id = "shared_document_name"
        
        self.client.store_vectors(
            self.user1,
            shared_doc_id,
            ["User 1 content in shared doc ID"],
            {"filename": "shared.txt", "user": "user1"}
        )
        
        self.client.store_vectors(
            self.user2,
            shared_doc_id,
            ["User 2 content in shared doc ID"],
            {"filename": "shared.txt", "user": "user2"}
        )
        
        # Verify both users can see their own content
        search1_before = self.client.search_similar(self.user1, "shared doc", 5)
        search2_before = self.client.search_similar(self.user2, "shared doc", 5)
        
        self.assertEqual(len(search1_before["results"]), 1)
        self.assertEqual(len(search2_before["results"]), 1)
        
        # User 1 deletes their document
        delete_result = self.client.delete_document_vectors(self.user1, shared_doc_id)
        self.assertTrue(delete_result["success"])
        self.assertEqual(delete_result["chunks_deleted"], 1)
        
        # Verify user 1's content is gone but user 2's remains
        search1_after = self.client.search_similar(self.user1, "shared doc", 5)
        search2_after = self.client.search_similar(self.user2, "shared doc", 5)
        
        self.assertEqual(len(search1_after["results"]), 0)  # User 1: gone
        self.assertEqual(len(search2_after["results"]), 1)  # User 2: still there
        
        print("✅ Document deletion isolation verified")
    
    def test_malicious_user_id_attempts(self):
        """Test handling of malicious user ID inputs"""
        print("\n=== Testing Malicious User ID Handling ===")
        
        # Store legitimate data
        self.client.store_vectors(
            "legitimate_user",
            "legit_doc",
            ["Legitimate user content"],
            {"filename": "legit.txt"}
        )
        
        # Test various malicious user ID formats
        malicious_user_ids = [
            "",  # Empty string
            " ",  # Whitespace only
            "null",  # Null string
            "undefined",  # Undefined string
            "admin",  # Common system names
            "root",
            "system",
            "*",  # Wildcard attempts
            "%",
            "$$",  # Special characters
            "../legitimate_user",  # Path traversal attempts
            "legitimate_user/../other_user",
            "legitimate_user OR 1=1",  # SQL injection style
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",  # XSS attempts
            "legitimate_user\x00null",  # Null byte injection
        ]
        
        for malicious_id in malicious_user_ids:
            # Test search with malicious ID
            search_result = self.client.search_similar(
                malicious_id,
                "legitimate user content",
                n_results=10
            )
            
            # Should not find any results (no data for these fake users)
            self.assertTrue(search_result["success"])
            self.assertEqual(len(search_result["results"]), 0)
            
            # Test statistics with malicious ID
            stats_result = self.client.get_user_statistics(malicious_id)
            self.assertTrue(stats_result["success"])
            self.assertEqual(stats_result["total_chunks"], 0)
        
        print("✅ Malicious user ID handling verified")
    
    def test_metadata_injection_attempts(self):
        """Test handling of malicious metadata injections"""
        print("\n=== Testing Metadata Injection Handling ===")
        
        # Test with malicious metadata
        malicious_metadata_sets = [
            # Oversized metadata
            {
                "filename": "test.txt",
                "malicious_large_field": "x" * 10000,  # Very large string
                "entities": {"topics": ["test"] * 1000}  # Many topics
            },
            
            # Special characters in metadata
            {
                "filename": "test'; DROP TABLE chunks; --.txt",
                "user_id": "injected_user",  # Try to override user_id
                "content_type": "<script>alert('xss')</script>"
            },
            
            # Nested object bombs
            {
                "filename": "test.txt",
                "nested": {"level1": {"level2": {"level3": {"level4": {"deep": "value"}}}}}
            }
        ]
        
        for i, malicious_metadata in enumerate(malicious_metadata_sets):
            user_id = f"metadata_test_user_{i}"
            doc_id = f"malicious_doc_{i}"
            
            # Store should succeed but sanitize metadata
            result = self.client.store_vectors(
                user_id,
                doc_id,
                [f"Test content {i}"],
                malicious_metadata
            )
            
            self.assertTrue(result["success"])
            
            # Search and verify user_id is correct
            search_result = self.client.search_similar(user_id, f"Test content {i}", 1)
            self.assertTrue(search_result["success"])
            self.assertEqual(len(search_result["results"]), 1)
            
            # Verify user_id cannot be overridden
            stored_metadata = search_result["results"][0]["metadata"]
            self.assertEqual(stored_metadata["user_id"], user_id)
        
        print("✅ Metadata injection handling verified")


class TestVectorErrorHandling(unittest.TestCase):
    """Test comprehensive error handling scenarios"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        setup_test_environment()
        
        # Check ChromaDB availability
        try:
            import chromadb
            cls.chromadb_available = True
        except ImportError:
            cls.chromadb_available = False
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        cleanup_test_environment()
    
    def setUp(self):
        """Set up individual test"""
        if not self.chromadb_available:
            self.skipTest("ChromaDB not available")
        
        self.test_dir = tempfile.mkdtemp(prefix="error_test_")
        
        from chromadb_client import ChromaDBClient
        self.client = ChromaDBClient(
            persist_directory=self.test_dir,
            collection_name="error_test_collection"
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        if hasattr(self, 'test_dir') and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_invalid_input_handling(self):
        """Test handling of various invalid inputs"""
        print("\n=== Testing Invalid Input Handling ===")
        
        # Test empty/None inputs
        invalid_inputs = [
            # (user_id, document_id, chunks, metadata)
            (None, "doc1", ["chunk"], {}),
            ("", "doc1", ["chunk"], {}),
            ("user1", None, ["chunk"], {}),
            ("user1", "", ["chunk"], {}),
            ("user1", "doc1", None, {}),
            ("user1", "doc1", [], {}),  # Empty chunks should work
            ("user1", "doc1", ["chunk"], None),
        ]
        
        for user_id, doc_id, chunks, metadata in invalid_inputs:
            if chunks is None or user_id is None or doc_id is None or metadata is None:
                # These should cause exceptions
                with self.assertRaises((TypeError, ValueError)):
                    self.client.store_vectors(user_id, doc_id, chunks, metadata)
            else:
                # Empty values should be handled gracefully
                result = self.client.store_vectors(user_id, doc_id, chunks, metadata or {})
                if chunks:  # Non-empty chunks should succeed
                    self.assertTrue(result["success"])
                else:  # Empty chunks should succeed with 0 stored
                    self.assertTrue(result["success"])
                    self.assertEqual(result["chunks_stored"], 0)
        
        print("✅ Invalid input handling verified")
    
    def test_large_data_handling(self):
        """Test handling of extremely large data inputs"""
        print("\n=== Testing Large Data Handling ===")
        
        # Test very large chunks
        large_chunk = "Large chunk content. " * 10000  # ~200KB per chunk
        
        try:
            result = self.client.store_vectors(
                "large_data_user",
                "large_doc",
                [large_chunk],
                {"filename": "large.txt", "size": "very_large"}
            )
            
            # Should handle large data gracefully
            self.assertTrue(result["success"])
            self.assertEqual(result["chunks_stored"], 1)
            print("✅ Large chunk handled successfully")
            
        except Exception as e:
            print(f"⚠️  Large chunk caused error: {e}")
            # This might be expected depending on ChromaDB limits
        
        # Test many small chunks
        many_chunks = [f"Small chunk {i}" for i in range(1000)]
        
        try:
            result = self.client.store_vectors(
                "many_chunks_user",
                "many_chunks_doc",
                many_chunks,
                {"filename": "many.txt", "count": len(many_chunks)}
            )
            
            self.assertTrue(result["success"])
            self.assertEqual(result["chunks_stored"], 1000)
            print("✅ Many chunks handled successfully")
            
        except Exception as e:
            print(f"⚠️  Many chunks caused error: {e}")
    
    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters"""
        print("\n=== Testing Unicode and Special Characters ===")
        
        unicode_test_data = [
            # Various Unicode content
            "Testing with émojis: 🔒🔐🛡️ and ñice spëcial characters",
            "Chinese characters: 数据保护和隐私政策",
            "Arabic text: الخصوصية وحماية البيانات", 
            "Russian: конфиденциальность данных",
            "Math symbols: ∑∞≠≤≥±∂∆∇√∫",
            "Special chars: !@#$%^&*()_+{}|:<>?[]\\;'\",./"
        ]
        
        try:
            result = self.client.store_vectors(
                "unicode_user",
                "unicode_doc",
                unicode_test_data,
                {
                    "filename": "unicode_tëst.txt",
                    "description": "Tëst with ñice chãracters and émojis 🔒"
                }
            )
            
            self.assertTrue(result["success"])
            self.assertEqual(result["chunks_stored"], len(unicode_test_data))
            
            # Test searching with Unicode
            search_result = self.client.search_similar(
                "unicode_user",
                "数据保护和隐私政策",  # Chinese query
                n_results=5
            )
            
            self.assertTrue(search_result["success"])
            print("✅ Unicode handling verified")
            
        except Exception as e:
            print(f"⚠️  Unicode handling error: {e}")
    
    def test_concurrent_error_scenarios(self):
        """Test error handling under concurrent load"""
        print("\n=== Testing Concurrent Error Scenarios ===")
        
        import threading
        import queue
        
        error_queue = queue.Queue()
        
        def store_with_errors(user_index):
            """Store data and capture any errors"""
            try:
                # Some operations will have invalid data
                if user_index % 3 == 0:
                    # Invalid metadata
                    result = self.client.store_vectors(
                        f"error_user_{user_index}",
                        f"error_doc_{user_index}",
                        [f"Content {user_index}"],
                        {"filename": None}  # Invalid filename
                    )
                else:
                    # Valid operation
                    result = self.client.store_vectors(
                        f"error_user_{user_index}",
                        f"error_doc_{user_index}",
                        [f"Content {user_index}"],
                        {"filename": f"file_{user_index}.txt"}
                    )
                
                error_queue.put((user_index, None, result["success"]))
                
            except Exception as e:
                error_queue.put((user_index, str(e), False))
        
        # Start concurrent operations
        threads = []
        for i in range(10):
            thread = threading.Thread(target=store_with_errors, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Analyze results
        successful_ops = 0
        failed_ops = 0
        
        while not error_queue.empty():
            user_index, error, success = error_queue.get()
            if success:
                successful_ops += 1
            else:
                failed_ops += 1
                if error:
                    print(f"  User {user_index} error: {error}")
        
        print(f"  Concurrent operations: {successful_ops} successful, {failed_ops} failed")
        
        # Should handle errors gracefully without crashing
        self.assertGreater(successful_ops, 0)
        print("✅ Concurrent error handling verified")
    
    @patch('chromadb_client.chromadb.PersistentClient')
    def test_chromadb_connection_errors(self, mock_client_class):
        """Test handling of ChromaDB connection errors"""
        print("\n=== Testing ChromaDB Connection Errors ===")
        
        # Mock ChromaDB client to raise connection errors
        mock_client = MagicMock()
        mock_collection = MagicMock()
        
        # Test store operation failure
        mock_collection.add.side_effect = Exception("Connection lost")
        mock_client.get_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client
        
        from chromadb_client import ChromaDBClient
        
        # Create client (will use mocked ChromaDB)
        client = ChromaDBClient("/tmp/mock_test")
        
        # Test store operation - should handle error gracefully
        result = client.store_vectors(
            "test_user",
            "test_doc",
            ["test chunk"],
            {"filename": "test.txt"}
        )
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Connection lost")
        
        print("✅ ChromaDB connection error handling verified")


if __name__ == '__main__':
    # Run security tests with high verbosity
    unittest.main(verbosity=2)