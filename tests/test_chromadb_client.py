#!/usr/bin/env python3
"""
Unit tests for ChromaDB client functionality
Tests all CRUD operations, user isolation, and error handling
"""

import unittest
import tempfile
import shutil
import json
import sys
import os
from unittest.mock import patch, MagicMock

# Add project paths
sys.path.insert(0, '/home/ec2-user/redact-terraform/api_code')
sys.path.insert(0, '/home/ec2-user/redact-terraform/tests')

from test_auth_utils import setup_test_environment, cleanup_test_environment

class TestChromaDBClient(unittest.TestCase):
    """Test ChromaDB client operations"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        setup_test_environment()
        
        # Check if ChromaDB is available
        try:
            import chromadb
            cls.chromadb_available = True
        except ImportError:
            cls.chromadb_available = False
            print("⚠️  ChromaDB not available, skipping ChromaDB tests")
    
    def setUp(self):
        """Set up test fixtures"""
        if not self.chromadb_available:
            self.skipTest("ChromaDB not available")
        
        # Create temporary directory for each test
        self.test_dir = tempfile.mkdtemp(prefix="chromadb_test_")
        
        # Import after setting up environment
        from chromadb_client import ChromaDBClient
        self.client = ChromaDBClient(
            persist_directory=self.test_dir,
            collection_name="test_collection"
        )
        
        # Test data
        self.test_user1 = "test_user_001"
        self.test_user2 = "test_user_002"
        self.test_doc1 = "doc_001"
        self.test_doc2 = "doc_002"
        
        self.test_chunks = [
            "This document discusses data privacy policies and GDPR compliance requirements.",
            "The second section covers security measures and data protection protocols.",
            "Third section explains user rights and data processing procedures."
        ]
        
        self.test_metadata = {
            "filename": "privacy_policy.txt",
            "content_type": "text/plain",
            "created_date": "2024-01-15T10:30:00Z",
            "file_size": 1024,
            "entities": {
                "topics": ["privacy", "security", "GDPR"],
                "people": ["Data Protection Officer"],
                "organizations": ["Company Inc."]
            },
            "content_analysis": {
                "key_topics": ["data protection", "privacy rights", "compliance"]
            }
        }
    
    def tearDown(self):
        """Clean up test fixtures"""
        if hasattr(self, 'test_dir') and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        cleanup_test_environment()
    
    def test_client_initialization(self):
        """Test ChromaDB client initialization"""
        self.assertIsNotNone(self.client)
        self.assertIsNotNone(self.client.client)
        self.assertIsNotNone(self.client.collection)
        self.assertEqual(self.client.collection_name, "test_collection")
        self.assertEqual(self.client.persist_directory, self.test_dir)
    
    def test_generate_document_id(self):
        """Test document ID generation"""
        # Test basic ID generation
        doc_id = self.client.generate_document_id(self.test_user1, self.test_doc1, 0)
        self.assertIsInstance(doc_id, str)
        self.assertEqual(len(doc_id), 16)  # Should be 16 chars (SHA256[:16])
        
        # Test consistency
        doc_id2 = self.client.generate_document_id(self.test_user1, self.test_doc1, 0)
        self.assertEqual(doc_id, doc_id2)
        
        # Test uniqueness
        different_chunk = self.client.generate_document_id(self.test_user1, self.test_doc1, 1)
        self.assertNotEqual(doc_id, different_chunk)
        
        different_user = self.client.generate_document_id(self.test_user2, self.test_doc1, 0)
        self.assertNotEqual(doc_id, different_user)
        
        different_doc = self.client.generate_document_id(self.test_user1, self.test_doc2, 0)
        self.assertNotEqual(doc_id, different_doc)
    
    def test_store_vectors_success(self):
        """Test successful vector storage"""
        result = self.client.store_vectors(
            user_id=self.test_user1,
            document_id=self.test_doc1,
            chunks=self.test_chunks,
            metadata=self.test_metadata
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["chunks_stored"], len(self.test_chunks))
        self.assertEqual(result["document_id"], self.test_doc1)
        self.assertEqual(result["collection"], "test_collection")
        self.assertIsInstance(result["chunk_ids"], list)
        self.assertEqual(len(result["chunk_ids"]), len(self.test_chunks))
    
    def test_store_vectors_empty_chunks(self):
        """Test storing empty chunks"""
        result = self.client.store_vectors(
            user_id=self.test_user1,
            document_id=self.test_doc1,
            chunks=[],
            metadata=self.test_metadata
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["chunks_stored"], 0)
    
    def test_store_vectors_minimal_metadata(self):
        """Test storing with minimal metadata"""
        minimal_metadata = {"filename": "test.txt"}
        
        result = self.client.store_vectors(
            user_id=self.test_user1,
            document_id=self.test_doc1,
            chunks=["Test chunk"],
            metadata=minimal_metadata
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["chunks_stored"], 1)
    
    def test_search_similar_success(self):
        """Test successful vector search"""
        # First store some vectors
        self.client.store_vectors(
            user_id=self.test_user1,
            document_id=self.test_doc1,
            chunks=self.test_chunks,
            metadata=self.test_metadata
        )
        
        # Search for similar content
        result = self.client.search_similar(
            user_id=self.test_user1,
            query_text="data privacy and GDPR compliance",
            n_results=3
        )
        
        self.assertTrue(result["success"])
        self.assertIsInstance(result["results"], list)
        self.assertGreater(len(result["results"]), 0)
        self.assertEqual(result["total_results"], len(result["results"]))
        
        # Check result structure
        for result_item in result["results"]:
            self.assertIn("chunk_id", result_item)
            self.assertIn("text", result_item)
            self.assertIn("metadata", result_item)
            # distance might not be present in all ChromaDB versions
    
    def test_search_similar_user_isolation(self):
        """Test that search results are isolated by user"""
        # Store vectors for user 1
        self.client.store_vectors(
            user_id=self.test_user1,
            document_id=self.test_doc1,
            chunks=["User 1 document about privacy"],
            metadata={"filename": "user1_doc.txt"}
        )
        
        # Store vectors for user 2
        self.client.store_vectors(
            user_id=self.test_user2,
            document_id=self.test_doc1,
            chunks=["User 2 document about privacy"],
            metadata={"filename": "user2_doc.txt"}
        )
        
        # Search as user 1
        result1 = self.client.search_similar(
            user_id=self.test_user1,
            query_text="privacy",
            n_results=5
        )
        
        # Search as user 2
        result2 = self.client.search_similar(
            user_id=self.test_user2,
            query_text="privacy",
            n_results=5
        )
        
        self.assertTrue(result1["success"])
        self.assertTrue(result2["success"])
        
        # Each user should only see their own results
        self.assertEqual(len(result1["results"]), 1)
        self.assertEqual(len(result2["results"]), 1)
        
        # Verify user isolation in metadata
        self.assertEqual(result1["results"][0]["metadata"]["user_id"], self.test_user1)
        self.assertEqual(result2["results"][0]["metadata"]["user_id"], self.test_user2)
    
    def test_search_similar_no_results(self):
        """Test search with no matching results"""
        result = self.client.search_similar(
            user_id="nonexistent_user",
            query_text="something that doesn't exist",
            n_results=5
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["results"]), 0)
        self.assertEqual(result["total_results"], 0)
    
    def test_search_with_metadata_filters(self):
        """Test search with metadata filters"""
        # Store vectors with different metadata
        self.client.store_vectors(
            user_id=self.test_user1,
            document_id=self.test_doc1,
            chunks=["Text document content"],
            metadata={"filename": "document.txt", "content_type": "text/plain"}
        )
        
        self.client.store_vectors(
            user_id=self.test_user1,
            document_id=self.test_doc2,
            chunks=["PDF document content"],
            metadata={"filename": "document.pdf", "content_type": "application/pdf"}
        )
        
        # Search with filename filter
        result = self.client.search_similar(
            user_id=self.test_user1,
            query_text="document content",
            n_results=5,
            filter_metadata={"filename": "document.txt"}
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["metadata"]["filename"], "document.txt")
        
        # Search with content_type filter
        result = self.client.search_similar(
            user_id=self.test_user1,
            query_text="document content",
            n_results=5,
            filter_metadata={"content_type": "application/pdf"}
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["metadata"]["content_type"], "application/pdf")
    
    def test_delete_document_vectors_success(self):
        """Test successful document deletion"""
        # First store some vectors
        self.client.store_vectors(
            user_id=self.test_user1,
            document_id=self.test_doc1,
            chunks=self.test_chunks,
            metadata=self.test_metadata
        )
        
        # Verify they were stored
        search_result = self.client.search_similar(
            user_id=self.test_user1,
            query_text="privacy",
            n_results=5
        )
        self.assertGreater(len(search_result["results"]), 0)
        
        # Delete the document
        delete_result = self.client.delete_document_vectors(self.test_user1, self.test_doc1)
        
        self.assertTrue(delete_result["success"])
        self.assertEqual(delete_result["chunks_deleted"], len(self.test_chunks))
        self.assertEqual(delete_result["document_id"], self.test_doc1)
        
        # Verify they were deleted
        search_result_after = self.client.search_similar(
            user_id=self.test_user1,
            query_text="privacy",
            n_results=5
        )
        self.assertEqual(len(search_result_after["results"]), 0)
    
    def test_delete_document_vectors_user_isolation(self):
        """Test that deletion respects user isolation"""
        # Store same document for two users
        self.client.store_vectors(
            user_id=self.test_user1,
            document_id=self.test_doc1,
            chunks=["User 1 content"],
            metadata={"filename": "shared_doc.txt"}
        )
        
        self.client.store_vectors(
            user_id=self.test_user2,
            document_id=self.test_doc1,
            chunks=["User 2 content"],
            metadata={"filename": "shared_doc.txt"}
        )
        
        # Delete document for user 1
        delete_result = self.client.delete_document_vectors(self.test_user1, self.test_doc1)
        self.assertTrue(delete_result["success"])
        self.assertEqual(delete_result["chunks_deleted"], 1)
        
        # Verify user 1's content is gone but user 2's remains
        search_user1 = self.client.search_similar(
            user_id=self.test_user1,
            query_text="content",
            n_results=5
        )
        search_user2 = self.client.search_similar(
            user_id=self.test_user2,
            query_text="content",
            n_results=5
        )
        
        self.assertEqual(len(search_user1["results"]), 0)
        self.assertEqual(len(search_user2["results"]), 1)
    
    def test_delete_nonexistent_document(self):
        """Test deleting a document that doesn't exist"""
        result = self.client.delete_document_vectors("nonexistent_user", "nonexistent_doc")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["chunks_deleted"], 0)
        self.assertIn("message", result)
    
    def test_get_user_statistics_success(self):
        """Test getting user statistics"""
        # Store vectors for user 1
        self.client.store_vectors(
            user_id=self.test_user1,
            document_id=self.test_doc1,
            chunks=self.test_chunks,
            metadata=self.test_metadata
        )
        
        # Store another document for user 1
        self.client.store_vectors(
            user_id=self.test_user1,
            document_id=self.test_doc2,
            chunks=["Another document"],
            metadata={"filename": "another.txt"}
        )
        
        # Store vectors for user 2 (should not appear in user 1 stats)
        self.client.store_vectors(
            user_id=self.test_user2,
            document_id=self.test_doc1,
            chunks=["User 2 document"],
            metadata={"filename": "user2.txt"}
        )
        
        # Get stats for user 1
        stats = self.client.get_user_statistics(self.test_user1)
        
        self.assertTrue(stats["success"])
        self.assertEqual(stats["total_chunks"], len(self.test_chunks) + 1)  # 3 + 1
        self.assertEqual(stats["unique_documents"], 2)
        self.assertGreater(stats["total_size"], 0)
        self.assertIn("documents", stats)
        self.assertIn(self.test_doc1, stats["documents"])
        self.assertIn(self.test_doc2, stats["documents"])
        
        # Get stats for user 2
        stats2 = self.client.get_user_statistics(self.test_user2)
        
        self.assertTrue(stats2["success"])
        self.assertEqual(stats2["total_chunks"], 1)
        self.assertEqual(stats2["unique_documents"], 1)
    
    def test_get_user_statistics_empty(self):
        """Test getting statistics for user with no data"""
        stats = self.client.get_user_statistics("empty_user")
        
        self.assertTrue(stats["success"])
        self.assertEqual(stats["total_chunks"], 0)
        self.assertEqual(stats["unique_documents"], 0)
        self.assertEqual(stats["total_size"], 0)
    
    def test_reset_collection(self):
        """Test collection reset functionality"""
        # Store some data
        self.client.store_vectors(
            user_id=self.test_user1,
            document_id=self.test_doc1,
            chunks=["Test content"],
            metadata={"filename": "test.txt"}
        )
        
        # Verify data exists
        stats_before = self.client.get_user_statistics(self.test_user1)
        self.assertEqual(stats_before["total_chunks"], 1)
        
        # Reset collection
        reset_result = self.client.reset_collection()
        self.assertTrue(reset_result["success"])
        
        # Verify data is gone
        stats_after = self.client.get_user_statistics(self.test_user1)
        self.assertEqual(stats_after["total_chunks"], 0)
    
    def test_error_handling(self):
        """Test error handling in various scenarios"""
        # Test with invalid user data
        with patch.object(self.client.collection, 'add', side_effect=Exception("Mock error")):
            result = self.client.store_vectors(
                user_id=self.test_user1,
                document_id=self.test_doc1,
                chunks=["Test"],
                metadata={}
            )
            self.assertFalse(result["success"])
            self.assertIn("error", result)
        
        # Test search error handling
        with patch.object(self.client.collection, 'query', side_effect=Exception("Mock search error")):
            result = self.client.search_similar(
                user_id=self.test_user1,
                query_text="test",
                n_results=1
            )
            self.assertFalse(result["success"])
            self.assertIn("error", result)
            self.assertEqual(result["results"], [])
    
    def test_large_batch_operations(self):
        """Test with larger batches of data"""
        # Create a large set of chunks
        large_chunks = [f"This is chunk {i} with some content about data processing and privacy." 
                       for i in range(50)]
        
        # Store large batch
        result = self.client.store_vectors(
            user_id=self.test_user1,
            document_id="large_doc",
            chunks=large_chunks,
            metadata={"filename": "large_document.txt"}
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["chunks_stored"], 50)
        
        # Search should work with large dataset
        search_result = self.client.search_similar(
            user_id=self.test_user1,
            query_text="data processing",
            n_results=10
        )
        
        self.assertTrue(search_result["success"])
        self.assertGreater(len(search_result["results"]), 0)
        self.assertLessEqual(len(search_result["results"]), 10)
        
        # Statistics should reflect large dataset
        stats = self.client.get_user_statistics(self.test_user1)
        self.assertEqual(stats["total_chunks"], 50)
        self.assertEqual(stats["unique_documents"], 1)

class TestChromaDBClientSingleton(unittest.TestCase):
    """Test the singleton ChromaDB client functionality"""
    
    def setUp(self):
        """Set up test environment"""
        setup_test_environment()
        
        # Reset singleton
        import chromadb_client
        chromadb_client._chromadb_client = None
    
    def tearDown(self):
        """Clean up test environment"""
        cleanup_test_environment()
        
        # Reset singleton
        import chromadb_client
        chromadb_client._chromadb_client = None
    
    def test_singleton_behavior(self):
        """Test that get_chromadb_client returns the same instance"""
        if not TestChromaDBClient.chromadb_available:
            self.skipTest("ChromaDB not available")
        
        from chromadb_client import get_chromadb_client
        
        client1 = get_chromadb_client()
        client2 = get_chromadb_client()
        
        self.assertIs(client1, client2)
        self.assertIsNotNone(client1)
    
    def test_environment_variable_configuration(self):
        """Test configuration via environment variables"""
        if not TestChromaDBClient.chromadb_available:
            self.skipTest("ChromaDB not available")
        
        # Set custom environment variables
        os.environ['CHROMADB_PERSIST_DIR'] = '/tmp/custom_test_chromadb'
        os.environ['CHROMADB_COLLECTION'] = 'custom_collection'
        
        from chromadb_client import get_chromadb_client
        
        client = get_chromadb_client()
        self.assertEqual(client.persist_directory, '/tmp/custom_test_chromadb')
        self.assertEqual(client.collection_name, 'custom_collection')


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)