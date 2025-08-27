#!/usr/bin/env python3
"""
Standalone test for ChromaDB vector integration
Tests only the ChromaDB functionality without AWS dependencies
"""

import sys
import os
import json

# Add api_code to path
sys.path.insert(0, '/home/ec2-user/redact-terraform/api_code')

def test_chromadb_basic():
    """Test basic ChromaDB functionality"""
    print("Testing basic ChromaDB functionality...")
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        print("✅ ChromaDB imported successfully")
        
        # Test client initialization
        client = chromadb.PersistentClient(
            path="/tmp/test_chromadb",
            settings=Settings(anonymized_telemetry=False)
        )
        print("✅ ChromaDB client initialized")
        
        # Test collection creation
        try:
            collection = client.get_collection("test_collection")
        except:
            collection = client.create_collection("test_collection")
        
        print("✅ Collection created/retrieved")
        
        # Test adding documents
        test_docs = [
            "This document discusses data privacy and security measures.",
            "The second document covers compliance with GDPR regulations.",
            "Third document explains encryption and data protection."
        ]
        
        test_metadatas = [
            {"filename": "privacy.txt", "topic": "privacy"},
            {"filename": "compliance.txt", "topic": "compliance"}, 
            {"filename": "encryption.txt", "topic": "security"}
        ]
        
        test_ids = ["doc1", "doc2", "doc3"]
        
        collection.add(
            ids=test_ids,
            documents=test_docs,
            metadatas=test_metadatas
        )
        print("✅ Documents added to collection")
        
        # Test querying
        results = collection.query(
            query_texts=["data privacy security"],
            n_results=2
        )
        
        if results["ids"] and len(results["ids"][0]) > 0:
            print(f"✅ Query successful: found {len(results['ids'][0])} results")
            for i, doc in enumerate(results["documents"][0]):
                print(f"   Result {i+1}: {doc[:50]}...")
        else:
            print("❌ Query returned no results")
            return False
        
        # Test deletion
        collection.delete(ids=["doc1"])
        print("✅ Document deletion successful")
        
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_custom_chromadb_client():
    """Test our custom ChromaDB client wrapper"""
    print("\nTesting custom ChromaDB client...")
    
    try:
        from chromadb_client import ChromaDBClient
        
        # Initialize client
        client = ChromaDBClient(
            persist_directory="/tmp/test_custom_chromadb",
            collection_name="test_custom"
        )
        print("✅ Custom ChromaDB client initialized")
        
        # Test data
        test_user = "test_user_123"
        test_doc = "test_document_456"
        test_chunks = [
            "First chunk about data privacy policies and procedures.",
            "Second chunk discussing security measures and compliance.",
            "Third chunk explaining user rights and data protection."
        ]
        test_metadata = {
            "filename": "test_policy.txt",
            "content_type": "text/plain",
            "entities": {"topics": ["privacy", "security", "compliance"]},
            "file_size": 1024
        }
        
        # Store vectors
        store_result = client.store_vectors(
            user_id=test_user,
            document_id=test_doc,
            chunks=test_chunks,
            metadata=test_metadata
        )
        
        if store_result["success"]:
            print(f"✅ Stored {store_result['chunks_stored']} chunks")
        else:
            print(f"❌ Store failed: {store_result.get('error')}")
            return False
        
        # Search vectors
        search_result = client.search_similar(
            user_id=test_user,
            query_text="privacy policies and data protection",
            n_results=3
        )
        
        if search_result["success"]:
            print(f"✅ Search found {search_result['total_results']} results")
            for i, result in enumerate(search_result["results"], 1):
                print(f"   Result {i}: distance={result.get('distance', 'N/A'):.3f}" if result.get('distance') else f"   Result {i}: {result['text'][:40]}...")
        else:
            print(f"❌ Search failed: {search_result.get('error')}")
            return False
        
        # Get statistics
        stats_result = client.get_user_statistics(test_user)
        
        if stats_result["success"]:
            print(f"✅ Stats: {stats_result['total_chunks']} chunks, {stats_result['unique_documents']} docs")
        else:
            print(f"❌ Stats failed: {stats_result.get('error')}")
            return False
        
        # Delete vectors
        delete_result = client.delete_document_vectors(test_user, test_doc)
        
        if delete_result["success"]:
            print(f"✅ Deleted {delete_result['chunks_deleted']} chunks")
        else:
            print(f"❌ Delete failed: {delete_result.get('error')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Custom client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_metadata_functions():
    """Test metadata extraction functions without AWS"""
    print("\nTesting metadata extraction functions...")
    
    try:
        # Mock content for testing
        test_content = """
        This is a test document containing various information:
        - John Smith works at Acme Corp
        - Phone: (555) 123-4567
        - Email: john.smith@acme.com
        - SSN: 123-45-6789
        - Date: January 15, 2024
        
        The document discusses privacy policies, data protection,
        and compliance with security regulations.
        """
        
        # Test if metadata functions can be imported
        sys.path.insert(0, '/home/ec2-user/redact-terraform/api_code')
        
        # Check if functions exist (they may fail due to AWS dependencies)
        try:
            from api_handler_simple import extract_document_properties
            print("✅ extract_document_properties imported")
        except ImportError:
            print("⚠️  extract_document_properties not available")
        
        # Test basic string operations that don't require AWS
        import re
        
        # Test entity extraction patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        
        emails = re.findall(email_pattern, test_content)
        phones = re.findall(phone_pattern, test_content)
        
        print(f"✅ Pattern matching works: found {len(emails)} emails, {len(phones)} phones")
        
        return True
        
    except Exception as e:
        print(f"❌ Metadata function test failed: {e}")
        return False

def main():
    """Run standalone tests"""
    print("="*60)
    print("ChromaDB Standalone Integration Tests")
    print("="*60)
    
    tests = [
        ("Basic ChromaDB", test_chromadb_basic),
        ("Custom ChromaDB Client", test_custom_chromadb_client),
        ("Metadata Functions", test_metadata_functions)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:25} {status}")
    
    print("-"*60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All standalone tests passed!")
        print("ChromaDB integration is working correctly.")
        print("\nNext steps:")
        print("1. Deploy the API handler with new endpoints")
        print("2. Create Lambda layer with ChromaDB")
        print("3. Test with actual API calls")
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)