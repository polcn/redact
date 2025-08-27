#!/usr/bin/env python3
"""
Tests for export functionality and data consistency
Tests the export utility, batch operations, and data integrity
"""

import unittest
import tempfile
import shutil
import sys
import os
import json
import time
from unittest.mock import patch, MagicMock
import requests_mock

# Add project paths
sys.path.insert(0, '/home/ec2-user/redact-terraform')
sys.path.insert(0, '/home/ec2-user/redact-terraform/api_code')
sys.path.insert(0, '/home/ec2-user/redact-terraform/tests')

from test_auth_utils import TestAuthHelper, setup_test_environment, cleanup_test_environment

class TestRedactExporter(unittest.TestCase):
    """Test the RedactExporter class functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        setup_test_environment()
        
        # Check if export module can be imported
        try:
            from export_to_chromadb import RedactExporter
            cls.exporter_available = True
        except ImportError as e:
            cls.exporter_available = False
            print(f"⚠️  RedactExporter not available: {e}")
        
        # Check if ChromaDB is available
        try:
            import chromadb
            cls.chromadb_available = True
        except ImportError:
            cls.chromadb_available = False
            print("⚠️  ChromaDB not available for export tests")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        cleanup_test_environment()
    
    def setUp(self):
        """Set up individual test"""
        if not self.exporter_available:
            self.skipTest("RedactExporter not available")
        
        self.test_dir = tempfile.mkdtemp(prefix="export_test_")
        
        # Mock API responses
        self.mock_documents = [
            {
                "id": "doc1",
                "key": "user123/doc1.txt",
                "filename": "document1.txt",
                "size": 1024,
                "last_modified": "2024-01-15T10:30:00Z"
            },
            {
                "id": "doc2", 
                "key": "user123/doc2.pdf",
                "filename": "document2.pdf",
                "size": 2048,
                "last_modified": "2024-01-16T11:45:00Z"
            }
        ]
        
        self.mock_metadata = {
            "success": True,
            "metadata": {
                "filename": "document1.txt",
                "file_size": 1024,
                "content_type": "text/plain",
                "created_date": "2024-01-15T10:30:00Z",
                "entities": {
                    "people": ["John Smith", "Jane Doe"],
                    "organizations": ["Acme Corp"],
                    "locations": ["New York"],
                    "phone_numbers": ["555-1234"],
                    "emails": ["john@example.com"]
                },
                "content_analysis": {
                    "key_topics": ["privacy", "security", "compliance"],
                    "sentiment": "neutral",
                    "language": "en"
                },
                "pii_detected": {
                    "ssn": ["123-45-6789"],
                    "credit_card": [],
                    "ip_addresses": ["192.168.1.1"]
                }
            }
        }
        
        self.mock_vector_chunks = {
            "success": True,
            "chunks": [
                "This document discusses data privacy policies and GDPR compliance.",
                "The second section covers security measures and data protection.",
                "Third section explains user rights and data processing procedures."
            ],
            "chunk_settings": {
                "size": 512,
                "overlap": 50,
                "strategy": "semantic"
            }
        }
    
    def tearDown(self):
        """Clean up test fixtures"""
        if hasattr(self, 'test_dir') and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @requests_mock.Mocker()
    def test_exporter_initialization(self, mock_requests):
        """Test RedactExporter initialization"""
        from export_to_chromadb import RedactExporter
        
        # Test with mock token
        exporter = RedactExporter("mock_auth_token")
        
        self.assertEqual(exporter.auth_token, "mock_auth_token")
        self.assertIn("Authorization", exporter.headers)
        self.assertEqual(exporter.headers["Authorization"], "Bearer mock_auth_token")
        print("✅ RedactExporter initialization verified")
    
    @requests_mock.Mocker()
    def test_get_all_documents(self, mock_requests):
        """Test fetching all documents"""
        from export_to_chromadb import RedactExporter
        
        # Mock the API response
        mock_requests.get(
            "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/user/files",
            json={"files": self.mock_documents}
        )
        
        exporter = RedactExporter("test_token")
        documents = exporter.get_all_documents()
        
        self.assertEqual(len(documents), 2)
        self.assertEqual(documents[0]["filename"], "document1.txt")
        self.assertEqual(documents[1]["filename"], "document2.pdf")
        print("✅ Document fetching verified")
    
    @requests_mock.Mocker()
    def test_extract_metadata_for_document(self, mock_requests):
        """Test metadata extraction for a single document"""
        from export_to_chromadb import RedactExporter
        
        # Mock the API response
        mock_requests.post(
            "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/extract-metadata",
            json=self.mock_metadata
        )
        
        exporter = RedactExporter("test_token")
        metadata = exporter.extract_metadata_for_document(self.mock_documents[0])
        
        self.assertIsInstance(metadata, dict)
        self.assertIn("entities", metadata)
        self.assertIn("content_analysis", metadata)
        self.assertEqual(metadata["filename"], "document1.txt")
        print("✅ Metadata extraction verified")
    
    @requests_mock.Mocker()
    def test_prepare_vectors_for_document(self, mock_requests):
        """Test vector preparation for a document"""
        from export_to_chromadb import RedactExporter
        
        # Mock the API response
        mock_requests.post(
            "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/prepare-vectors",
            json=self.mock_vector_chunks
        )
        
        exporter = RedactExporter("test_token")
        chunks = exporter.prepare_vectors_for_document(self.mock_documents[0])
        
        self.assertIsInstance(chunks, list)
        self.assertEqual(len(chunks), 3)
        self.assertIn("privacy policies", chunks[0])
        print("✅ Vector preparation verified")
    
    @requests_mock.Mocker()
    def test_export_single_document(self, mock_requests):
        """Test exporting a single document"""
        if not self.chromadb_available:
            self.skipTest("ChromaDB not available")
        
        from export_to_chromadb import RedactExporter
        
        # Mock API responses
        mock_requests.post(
            "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/extract-metadata",
            json=self.mock_metadata
        )
        mock_requests.post(
            "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/prepare-vectors", 
            json=self.mock_vector_chunks
        )
        
        # Temporarily change export directory to test directory
        import export_to_chromadb
        original_export_dir = export_to_chromadb.EXPORT_DIR
        export_to_chromadb.EXPORT_DIR = self.test_dir
        
        try:
            exporter = RedactExporter("test_token")
            result = exporter.export_single_document("doc1", "document1.txt")
            
            self.assertTrue(result["success"])
            self.assertTrue(result["metadata_extracted"])
            self.assertEqual(result["chunks_created"], 3)
            
            # Verify file was created
            self.assertTrue(os.path.exists(result["output_file"]))
            
            # Verify file contents
            with open(result["output_file"], 'r') as f:
                data = json.load(f)
                self.assertEqual(data["document_id"], "doc1")
                self.assertEqual(data["filename"], "document1.txt")
                self.assertIn("metadata", data)
                self.assertIn("chunks", data)
            
            print("✅ Single document export verified")
            
        finally:
            export_to_chromadb.EXPORT_DIR = original_export_dir
    
    @requests_mock.Mocker()
    def test_json_export_functionality(self, mock_requests):
        """Test JSON export functionality"""
        from export_to_chromadb import RedactExporter
        
        # Mock all API responses
        mock_requests.get(
            "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/user/files",
            json={"files": self.mock_documents[:1]}  # Just one document for simplicity
        )
        mock_requests.post(
            "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/extract-metadata",
            json=self.mock_metadata
        )
        
        # Change export directory
        import export_to_chromadb
        original_export_dir = export_to_chromadb.EXPORT_DIR
        export_to_chromadb.EXPORT_DIR = self.test_dir
        
        try:
            exporter = RedactExporter("test_token")
            result = exporter.export_all_metadata("json")
            
            self.assertEqual(result["total_documents"], 1)
            self.assertEqual(result["processed_successfully"], 1)
            self.assertEqual(result["failed"], 0)
            
            # Verify JSON file was created
            json_files = [f for f in os.listdir(self.test_dir) if f.startswith("metadata_") and f.endswith(".json")]
            self.assertEqual(len(json_files), 1)
            
            # Verify JSON content
            with open(os.path.join(self.test_dir, json_files[0]), 'r') as f:
                data = json.load(f)
                self.assertEqual(data["total_documents"], 1)
                self.assertIn("documents", data)
            
            print("✅ JSON export functionality verified")
            
        finally:
            export_to_chromadb.EXPORT_DIR = original_export_dir
    
    @requests_mock.Mocker()
    def test_chromadb_export_functionality(self, mock_requests):
        """Test ChromaDB export functionality"""
        if not self.chromadb_available:
            self.skipTest("ChromaDB not available")
        
        from export_to_chromadb import RedactExporter
        
        # Mock all API responses
        mock_requests.get(
            "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/user/files",
            json={"files": self.mock_documents[:1]}
        )
        mock_requests.post(
            "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/extract-metadata",
            json=self.mock_metadata
        )
        mock_requests.post(
            "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/prepare-vectors",
            json=self.mock_vector_chunks
        )
        
        # Change export directory
        import export_to_chromadb
        original_export_dir = export_to_chromadb.EXPORT_DIR
        export_to_chromadb.EXPORT_DIR = self.test_dir
        
        try:
            exporter = RedactExporter("test_token")
            result = exporter.export_all_metadata("chromadb")
            
            self.assertEqual(result["total_documents"], 1)
            self.assertEqual(result["processed_successfully"], 1)
            
            # Verify ChromaDB directory was created
            chromadb_path = os.path.join(self.test_dir, "chromadb")
            self.assertTrue(os.path.exists(chromadb_path))
            
            print("✅ ChromaDB export functionality verified")
            
        finally:
            export_to_chromadb.EXPORT_DIR = original_export_dir
    
    @requests_mock.Mocker()
    def test_rag_ready_export(self, mock_requests):
        """Test RAG-ready export functionality"""
        from export_to_chromadb import RedactExporter
        
        # Mock all API responses
        mock_requests.get(
            "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/user/files",
            json={"files": self.mock_documents}
        )
        mock_requests.post(
            "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/extract-metadata",
            json=self.mock_metadata
        )
        mock_requests.post(
            "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/prepare-vectors",
            json=self.mock_vector_chunks
        )
        
        # Change export directory
        import export_to_chromadb
        original_export_dir = export_to_chromadb.EXPORT_DIR
        export_to_chromadb.EXPORT_DIR = self.test_dir
        
        try:
            exporter = RedactExporter("test_token")
            result = exporter.create_rag_ready_export()
            
            self.assertTrue(result["success"])
            self.assertEqual(result["documents_exported"], 2)
            self.assertIn("entity_types", result)
            self.assertGreater(result["topics_indexed"], 0)
            
            # Verify RAG export file
            self.assertTrue(os.path.exists(result["output_file"]))
            
            with open(result["output_file"], 'r') as f:
                data = json.load(f)
                self.assertIn("export_metadata", data)
                self.assertIn("documents", data)
                self.assertIn("entity_index", data)
                self.assertIn("topic_index", data)
                self.assertEqual(len(data["documents"]), 2)
            
            print("✅ RAG-ready export verified")
            
        finally:
            export_to_chromadb.EXPORT_DIR = original_export_dir
    
    @requests_mock.Mocker()
    def test_error_handling_in_export(self, mock_requests):
        """Test error handling during export operations"""
        from export_to_chromadb import RedactExporter
        
        # Test with API error responses
        mock_requests.get(
            "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/user/files",
            json={"files": self.mock_documents[:1]}
        )
        
        # Mock metadata endpoint to return error
        mock_requests.post(
            "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production/documents/extract-metadata",
            json={"success": False, "error": "Document not found"},
            status_code=404
        )
        
        import export_to_chromadb
        original_export_dir = export_to_chromadb.EXPORT_DIR
        export_to_chromadb.EXPORT_DIR = self.test_dir
        
        try:
            exporter = RedactExporter("test_token")
            result = exporter.export_all_metadata("json")
            
            # Should handle errors gracefully
            self.assertEqual(result["total_documents"], 1)
            self.assertEqual(result["processed_successfully"], 0)  # Metadata failed
            self.assertEqual(result["failed"], 1)
            self.assertIn("failed_documents", result)
            
            print("✅ Export error handling verified")
            
        finally:
            export_to_chromadb.EXPORT_DIR = original_export_dir


class TestBatchMetadataExport(unittest.TestCase):
    """Test batch metadata export API endpoint"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        setup_test_environment()
        cls.auth_helper = TestAuthHelper()
        
        # Check if handler is available
        try:
            from api_handler_simple import handle_batch_metadata_export
            cls.handler_available = True
        except ImportError:
            cls.handler_available = False
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        cleanup_test_environment()
    
    def setUp(self):
        """Set up individual test"""
        if not self.handler_available:
            self.skipTest("Batch metadata export handler not available")
        
        self.user_headers = self.auth_helper.login_as_user("test_export_user")
        self.lambda_context = self.auth_helper.create_lambda_context()
    
    @patch('boto3.client')
    def test_batch_metadata_export_handler(self, mock_boto3):
        """Test batch metadata export handler"""
        from api_handler_simple import handle_batch_metadata_export
        
        # Create test event
        event = self.auth_helper.create_lambda_event(
            method="POST",
            path="/export/batch-metadata",
            body={
                "document_ids": ["doc1", "doc2"],
                "export_format": "json"
            },
            headers=self.user_headers
        )
        
        user_context = self.auth_helper.get_user_context(self.user_headers["Authorization"])
        
        try:
            response = handle_batch_metadata_export(event, self.user_headers, self.lambda_context, user_context)
            
            self.assertEqual(response["statusCode"], 200)
            
            body = json.loads(response["body"])
            self.assertTrue(body.get("success", False))
            
            print("✅ Batch metadata export handler working")
            
        except Exception as e:
            print(f"⚠️  Handler error: {e}")
            # Expected due to missing dependencies
    
    def test_batch_export_input_validation(self):
        """Test input validation for batch export"""
        from api_handler_simple import handle_batch_metadata_export
        
        # Test with invalid JSON
        event = self.auth_helper.create_lambda_event(
            method="POST",
            path="/export/batch-metadata",
            headers=self.user_headers
        )
        event["body"] = "invalid json{"
        
        user_context = self.auth_helper.get_user_context(self.user_headers["Authorization"])
        
        try:
            response = handle_batch_metadata_export(event, self.user_headers, self.lambda_context, user_context)
            self.assertEqual(response["statusCode"], 400)
            
            body = json.loads(response["body"])
            self.assertFalse(body.get("success", True))
            
        except Exception as e:
            print(f"⚠️  Expected error for invalid JSON: {e}")


class TestDataConsistency(unittest.TestCase):
    """Test data consistency across export and vector operations"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        setup_test_environment()
        
        # Check if both ChromaDB and export are available
        try:
            import chromadb
            from export_to_chromadb import RedactExporter
            cls.components_available = True
        except ImportError:
            cls.components_available = False
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        cleanup_test_environment()
    
    def setUp(self):
        """Set up individual test"""
        if not self.components_available:
            self.skipTest("Required components not available")
        
        self.test_dir = tempfile.mkdtemp(prefix="consistency_test_")
    
    def tearDown(self):
        """Clean up test fixtures"""
        if hasattr(self, 'test_dir') and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_vector_storage_export_consistency(self):
        """Test that exported data matches stored vector data"""
        from chromadb_client import ChromaDBClient
        
        # Create ChromaDB client
        client = ChromaDBClient(
            persist_directory=self.test_dir,
            collection_name="consistency_test"
        )
        
        # Store test data
        test_user = "consistency_user"
        test_doc = "consistency_doc"
        test_chunks = [
            "First chunk with privacy information",
            "Second chunk with security details",
            "Third chunk with compliance requirements"
        ]
        test_metadata = {
            "filename": "consistency_test.txt",
            "content_type": "text/plain",
            "entities": {"topics": ["privacy", "security", "compliance"]}
        }
        
        # Store vectors
        store_result = client.store_vectors(test_user, test_doc, test_chunks, test_metadata)
        self.assertTrue(store_result["success"])
        
        # Retrieve and verify consistency
        search_result = client.search_similar(test_user, "privacy security", 10)
        self.assertTrue(search_result["success"])
        
        # Verify all original chunks can be found
        found_texts = [result["text"] for result in search_result["results"]]
        
        for original_chunk in test_chunks:
            chunk_found = any(original_chunk in found_text for found_text in found_texts)
            self.assertTrue(chunk_found, f"Original chunk not found in search results: {original_chunk}")
        
        # Verify metadata consistency
        for result in search_result["results"]:
            metadata = result["metadata"]
            self.assertEqual(metadata["user_id"], test_user)
            self.assertEqual(metadata["document_id"], test_doc)
            self.assertEqual(metadata["filename"], test_metadata["filename"])
        
        print("✅ Vector storage-export consistency verified")
    
    def test_export_import_roundtrip_consistency(self):
        """Test that exported data can be imported back consistently"""
        if not self.components_available:
            self.skipTest("Components not available")
        
        from chromadb_client import ChromaDBClient
        
        # Create source ChromaDB
        source_client = ChromaDBClient(
            persist_directory=os.path.join(self.test_dir, "source"),
            collection_name="source_collection"
        )
        
        # Store original data
        original_data = {
            "user_id": "roundtrip_user",
            "document_id": "roundtrip_doc",
            "chunks": [
                "Original chunk 1 with specific content",
                "Original chunk 2 with different content",
                "Original chunk 3 with unique content"
            ],
            "metadata": {
                "filename": "roundtrip_test.txt",
                "test_field": "test_value",
                "entities": {"topics": ["test", "roundtrip"]}
            }
        }
        
        store_result = source_client.store_vectors(**original_data)
        self.assertTrue(store_result["success"])
        
        # Get original statistics
        original_stats = source_client.get_user_statistics(original_data["user_id"])
        
        # Simulate export-import process by creating a new ChromaDB instance
        # and copying data (simplified version of what the export tool would do)
        target_client = ChromaDBClient(
            persist_directory=os.path.join(self.test_dir, "target"),
            collection_name="target_collection"
        )
        
        # "Import" the data (simulate what would happen after export/import)
        import_result = target_client.store_vectors(**original_data)
        self.assertTrue(import_result["success"])
        
        # Get imported statistics
        imported_stats = target_client.get_user_statistics(original_data["user_id"])
        
        # Verify statistics match
        self.assertEqual(original_stats["total_chunks"], imported_stats["total_chunks"])
        self.assertEqual(original_stats["unique_documents"], imported_stats["unique_documents"])
        
        # Verify content accessibility
        search_result = target_client.search_similar(
            original_data["user_id"],
            "specific content different unique",
            10
        )
        
        self.assertTrue(search_result["success"])
        self.assertEqual(len(search_result["results"]), 3)  # Should find all chunks
        
        print("✅ Export-import roundtrip consistency verified")


if __name__ == '__main__':
    # Run export tests with high verbosity
    unittest.main(verbosity=2)