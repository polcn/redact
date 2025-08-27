#!/usr/bin/env python3
"""
RAG Workflow Example - Complete pipeline for document processing and vector storage

This script demonstrates the complete workflow:
1. Extract metadata from a document
2. Prepare vectors (chunk the document)
3. Store vectors in ChromaDB
4. Search for similar content
5. Use results for RAG-based queries
"""

import requests
import json
import base64
from typing import List, Dict, Any

# Configuration
API_BASE_URL = "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production"
AUTH_TOKEN = "YOUR_COGNITO_ID_TOKEN"  # Get from browser DevTools after logging in

def make_api_request(endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
    """Make an authenticated API request"""
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    url = f"{API_BASE_URL}{endpoint}"
    
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)
    elif method == "DELETE":
        response = requests.delete(url, headers=headers)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    return response.json()

def process_document_for_rag(document_id: str, filename: str) -> Dict:
    """
    Complete RAG pipeline for a document
    
    Args:
        document_id: S3 key or document ID
        filename: Original filename
    
    Returns:
        Dictionary with processing results
    """
    
    print(f"Processing document: {filename}")
    print("-" * 50)
    
    # Step 1: Extract metadata
    print("\n1. Extracting metadata...")
    metadata_response = make_api_request(
        "/documents/extract-metadata",
        method="POST",
        data={
            "document_id": document_id,
            "filename": filename,
            "extraction_types": ["all"]
        }
    )
    
    if not metadata_response.get("success"):
        print(f"Error extracting metadata: {metadata_response}")
        return {"error": "Metadata extraction failed"}
    
    metadata = metadata_response["metadata"]
    print(f"   - Extracted entities: {len(metadata.get('entities', {}))} types")
    if 'content_analysis' in metadata:
        topics = metadata['content_analysis'].get('key_topics', [])
        print(f"   - Key topics: {', '.join(topics[:3])}...")
    
    # Step 2: Prepare vectors (chunk the document)
    print("\n2. Preparing document chunks...")
    vector_prep_response = make_api_request(
        "/documents/prepare-vectors",
        method="POST",
        data={
            "document_id": document_id,
            "filename": filename,
            "chunk_size": 512,  # Characters per chunk
            "overlap": 50,      # Overlap between chunks
            "strategy": "semantic"  # Chunking strategy
        }
    )
    
    if not vector_prep_response.get("success"):
        print(f"Error preparing vectors: {vector_prep_response}")
        return {"error": "Vector preparation failed"}
    
    chunks = vector_prep_response["chunks"]
    print(f"   - Created {len(chunks)} chunks")
    print(f"   - Strategy: {vector_prep_response['chunking_strategy']}")
    print(f"   - Avg chunk size: {vector_prep_response['statistics']['average_chunk_size']} chars")
    
    # Step 3: Store vectors in ChromaDB
    print("\n3. Storing vectors in ChromaDB...")
    store_response = make_api_request(
        "/vectors/store",
        method="POST",
        data={
            "document_id": document_id,
            "chunks": chunks,
            "metadata": metadata
        }
    )
    
    if not store_response.get("success"):
        print(f"Error storing vectors: {store_response}")
        return {"error": "Vector storage failed"}
    
    print(f"   - Stored {store_response['chunks_stored']} chunks")
    print(f"   - Collection: {store_response['collection']}")
    print(f"   - Chunk IDs: {store_response['chunk_ids'][:3]}...")
    
    # Step 4: Test vector search
    print("\n4. Testing vector search...")
    test_query = "data privacy and security"  # Example query
    search_response = make_api_request(
        "/vectors/search",
        method="POST",
        data={
            "query": test_query,
            "n_results": 3,
            "filter": {"filename": filename}  # Optional: filter to this document
        }
    )
    
    if not search_response.get("success"):
        print(f"Error searching vectors: {search_response}")
    else:
        print(f"   - Query: '{test_query}'")
        print(f"   - Found {search_response['total_results']} relevant chunks")
        
        for i, result in enumerate(search_response['results'], 1):
            print(f"\n   Result {i}:")
            print(f"   - Distance: {result.get('distance', 'N/A')}")
            print(f"   - Text preview: {result['text'][:100]}...")
            print(f"   - Chunk index: {result['metadata'].get('chunk_index')}")
    
    # Step 5: Get user statistics
    print("\n5. Getting vector statistics...")
    stats_response = make_api_request("/vectors/stats")
    
    if stats_response.get("success"):
        print(f"   - Total chunks stored: {stats_response['total_chunks']}")
        print(f"   - Unique documents: {stats_response['unique_documents']}")
        print(f"   - Total storage size: {stats_response['total_size']} chars")
    
    return {
        "success": True,
        "metadata": metadata,
        "chunks_created": len(chunks),
        "chunks_stored": store_response.get("chunks_stored", 0),
        "search_test_results": search_response.get("total_results", 0)
    }

def rag_query_example(query: str, n_results: int = 5) -> Dict:
    """
    Example of using RAG for answering questions
    
    Args:
        query: User's question
        n_results: Number of relevant chunks to retrieve
    
    Returns:
        RAG response with context and answer
    """
    
    print(f"\nRAG Query: '{query}'")
    print("-" * 50)
    
    # Step 1: Search for relevant chunks
    print("\n1. Searching for relevant context...")
    search_response = make_api_request(
        "/vectors/search",
        method="POST",
        data={
            "query": query,
            "n_results": n_results
        }
    )
    
    if not search_response.get("success") or not search_response.get("results"):
        return {"error": "No relevant context found"}
    
    # Step 2: Collect context from search results
    context_chunks = []
    source_docs = set()
    
    for result in search_response["results"]:
        context_chunks.append(result["text"])
        source_docs.add(result["metadata"].get("filename", "unknown"))
    
    print(f"   - Found {len(context_chunks)} relevant chunks")
    print(f"   - From documents: {', '.join(source_docs)}")
    
    # Step 3: Prepare context for AI
    combined_context = "\n\n---\n\n".join(context_chunks)
    
    # Step 4: Generate AI response with context
    print("\n2. Generating AI response with context...")
    ai_prompt = f"""Based on the following context, please answer the question.

Context:
{combined_context}

Question: {query}

Answer:"""
    
    ai_response = make_api_request(
        "/documents/ai-summary",
        method="POST",
        data={
            "content": ai_prompt,
            "prompt": "Answer the question based only on the provided context. If the answer is not in the context, say so.",
            "model": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "max_tokens": 500
        }
    )
    
    if not ai_response.get("success"):
        return {"error": "AI generation failed", "details": ai_response}
    
    return {
        "success": True,
        "query": query,
        "answer": ai_response.get("summary", "No answer generated"),
        "sources": list(source_docs),
        "context_chunks": len(context_chunks),
        "model": ai_response.get("model_used")
    }

def delete_document_vectors(document_id: str) -> Dict:
    """Delete all vectors for a document"""
    
    print(f"\nDeleting vectors for document: {document_id}")
    
    response = make_api_request(
        f"/vectors/delete?document_id={document_id}",
        method="DELETE"
    )
    
    if response.get("success"):
        print(f"   - Deleted {response['chunks_deleted']} chunks")
    else:
        print(f"   - Error: {response}")
    
    return response

def main():
    """Example workflow"""
    
    print("\n" + "=" * 60)
    print("RAG Workflow Example - Document Processing Pipeline")
    print("=" * 60)
    
    # Example 1: Process a single document
    # Replace with actual document_id from your /user/files endpoint
    example_document = {
        "document_id": "processed/users/YOUR_USER_ID/20250827_123456_example.txt",
        "filename": "example.txt"
    }
    
    # Process document for RAG
    result = process_document_for_rag(
        example_document["document_id"],
        example_document["filename"]
    )
    
    if result.get("success"):
        print("\n" + "=" * 60)
        print("Document processed successfully!")
        print(f"- Metadata extracted: Yes")
        print(f"- Chunks created: {result['chunks_created']}")
        print(f"- Chunks stored: {result['chunks_stored']}")
        print(f"- Search test results: {result['search_test_results']}")
    
    # Example 2: RAG Query
    print("\n" + "=" * 60)
    print("Testing RAG Query...")
    print("=" * 60)
    
    rag_result = rag_query_example(
        "What are the main security considerations mentioned in the documents?"
    )
    
    if rag_result.get("success"):
        print("\n" + "=" * 60)
        print("RAG Query Result:")
        print(f"Question: {rag_result['query']}")
        print(f"Answer: {rag_result['answer']}")
        print(f"Sources: {', '.join(rag_result['sources'])}")
        print(f"Context chunks used: {rag_result['context_chunks']}")
    
    # Optional: Clean up vectors
    # delete_document_vectors(example_document["document_id"])

if __name__ == "__main__":
    # Before running, update AUTH_TOKEN with your actual Cognito token
    # You can get this from browser DevTools after logging into the app
    
    print("\nBefore running this script:")
    print("1. Log into the Redact app at https://redact.9thcube.com")
    print("2. Open browser DevTools (F12) > Network tab")
    print("3. Make any API request (e.g., refresh files list)")
    print("4. Find the Authorization header in the request")
    print("5. Copy the token (after 'Bearer ') and update AUTH_TOKEN above")
    print("\nThen run: python3 rag_workflow_example.py")
    
    # Uncomment to run the example
    # main()