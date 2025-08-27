#!/usr/bin/env python3
"""
Export Tool - Extract metadata and vectors from Redact for external ChromaDB

This script provides multiple methods to export data from Redact:
1. Direct API extraction - Get metadata for all your documents
2. Batch processing - Process multiple documents efficiently  
3. ChromaDB export - Export directly to external ChromaDB instance
4. JSON export - Export to JSON files for other systems
"""

import requests
import json
import base64
import os
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import chromadb
from chromadb.config import Settings

# Configuration
API_BASE_URL = "https://101pi5aiv5.execute-api.us-east-1.amazonaws.com/production"
AUTH_TOKEN = os.environ.get("REDACT_AUTH_TOKEN", "YOUR_COGNITO_ID_TOKEN")

# Export configuration
EXPORT_DIR = "./redact_export"
CHUNK_SIZE = 512  # Characters per chunk for vector preparation
CHUNK_OVERLAP = 50

class RedactExporter:
    """Export data from Redact application"""
    
    def __init__(self, auth_token: str = AUTH_TOKEN):
        self.auth_token = auth_token
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        self.api_base = API_BASE_URL
        
        # Create export directory
        os.makedirs(EXPORT_DIR, exist_ok=True)
        
    def make_api_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        """Make authenticated API request"""
        url = f"{self.api_base}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return {"error": str(e)}
    
    def get_all_documents(self) -> List[Dict]:
        """Get list of all user's documents"""
        print("Fetching document list...")
        response = self.make_api_request("/user/files")
        
        if "error" in response:
            print(f"Error fetching documents: {response['error']}")
            return []
        
        documents = response.get("files", [])
        print(f"Found {len(documents)} documents")
        return documents
    
    def extract_metadata_for_document(self, document: Dict) -> Dict:
        """Extract metadata for a single document"""
        document_id = document.get("id") or document.get("key")
        filename = document.get("filename", "unknown")
        
        print(f"  Extracting metadata for: {filename}")
        
        response = self.make_api_request(
            "/documents/extract-metadata",
            method="POST",
            data={
                "document_id": document_id,
                "filename": filename,
                "extraction_types": ["all"]
            }
        )
        
        if response.get("success"):
            return response["metadata"]
        else:
            print(f"    Error: {response.get('error', 'Unknown error')}")
            return {}
    
    def prepare_vectors_for_document(self, document: Dict) -> List[str]:
        """Prepare vector chunks for a document"""
        document_id = document.get("id") or document.get("key")
        filename = document.get("filename", "unknown")
        
        print(f"  Preparing vectors for: {filename}")
        
        response = self.make_api_request(
            "/documents/prepare-vectors",
            method="POST",
            data={
                "document_id": document_id,
                "filename": filename,
                "chunk_size": CHUNK_SIZE,
                "overlap": CHUNK_OVERLAP,
                "strategy": "semantic"
            }
        )
        
        if response.get("success"):
            return response.get("chunks", [])
        else:
            print(f"    Error: {response.get('error', 'Unknown error')}")
            return []
    
    def export_all_metadata(self, output_format: str = "json") -> Dict:
        """
        Export metadata for all documents
        
        Args:
            output_format: 'json', 'chromadb', or 'both'
        
        Returns:
            Summary of export operation
        """
        print("\n" + "="*60)
        print("Starting Metadata Export")
        print("="*60)
        
        # Get all documents
        documents = self.get_all_documents()
        if not documents:
            return {"error": "No documents found"}
        
        all_metadata = []
        all_vectors = []
        failed_docs = []
        
        # Process each document
        for i, doc in enumerate(documents, 1):
            print(f"\nProcessing document {i}/{len(documents)}:")
            
            try:
                # Extract metadata
                metadata = self.extract_metadata_for_document(doc)
                if metadata:
                    metadata["source_document"] = doc
                    all_metadata.append(metadata)
                
                # Prepare vectors if needed
                if output_format in ["chromadb", "both"]:
                    chunks = self.prepare_vectors_for_document(doc)
                    if chunks:
                        all_vectors.append({
                            "document": doc,
                            "metadata": metadata,
                            "chunks": chunks
                        })
                
                # Rate limiting
                time.sleep(0.5)  # Be nice to the API
                
            except Exception as e:
                print(f"  Failed: {e}")
                failed_docs.append(doc.get("filename", "unknown"))
        
        # Export to JSON
        if output_format in ["json", "both"]:
            json_file = self._export_to_json(all_metadata, all_vectors)
            print(f"\nExported to JSON: {json_file}")
        
        # Export to ChromaDB
        if output_format in ["chromadb", "both"]:
            chromadb_result = self._export_to_chromadb(all_vectors)
            print(f"\nExported to ChromaDB: {chromadb_result}")
        
        # Summary
        summary = {
            "total_documents": len(documents),
            "processed_successfully": len(all_metadata),
            "failed": len(failed_docs),
            "failed_documents": failed_docs,
            "export_format": output_format,
            "timestamp": datetime.now().isoformat()
        }
        
        print("\n" + "="*60)
        print("Export Summary:")
        print(f"  Total documents: {summary['total_documents']}")
        print(f"  Processed: {summary['processed_successfully']}")
        print(f"  Failed: {summary['failed']}")
        print("="*60)
        
        return summary
    
    def _export_to_json(self, metadata: List[Dict], vectors: List[Dict]) -> str:
        """Export data to JSON files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export metadata
        metadata_file = os.path.join(EXPORT_DIR, f"metadata_{timestamp}.json")
        with open(metadata_file, "w") as f:
            json.dump({
                "export_date": datetime.now().isoformat(),
                "total_documents": len(metadata),
                "documents": metadata
            }, f, indent=2)
        
        # Export vectors if available
        if vectors:
            vectors_file = os.path.join(EXPORT_DIR, f"vectors_{timestamp}.json")
            with open(vectors_file, "w") as f:
                json.dump({
                    "export_date": datetime.now().isoformat(),
                    "total_documents": len(vectors),
                    "chunk_size": CHUNK_SIZE,
                    "overlap": CHUNK_OVERLAP,
                    "documents": vectors
                }, f, indent=2)
        
        return metadata_file
    
    def _export_to_chromadb(self, vectors_data: List[Dict]) -> Dict:
        """Export directly to external ChromaDB instance"""
        
        # Initialize ChromaDB client (external instance)
        client = chromadb.PersistentClient(
            path=os.path.join(EXPORT_DIR, "chromadb"),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create or get collection
        try:
            collection = client.get_collection("redact_export")
            # Clear existing data
            collection.delete()
            collection = client.create_collection("redact_export")
        except:
            collection = client.create_collection("redact_export")
        
        total_chunks = 0
        
        # Add documents to ChromaDB
        for doc_data in vectors_data:
            document = doc_data["document"]
            metadata = doc_data["metadata"]
            chunks = doc_data["chunks"]
            
            # Prepare data for ChromaDB
            ids = []
            metadatas = []
            documents = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{document.get('id', 'unknown')}_{i}"
                ids.append(chunk_id)
                
                chunk_metadata = {
                    "filename": metadata.get("filename", "unknown"),
                    "document_id": document.get("id", "unknown"),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "file_size": metadata.get("file_size", 0),
                    "content_type": metadata.get("content_type", "unknown"),
                    "created_date": metadata.get("created_date", ""),
                }
                
                # Add entities if available
                if "entities" in metadata:
                    # Store as JSON string since ChromaDB has limitations on metadata
                    chunk_metadata["entities"] = json.dumps(metadata["entities"])
                
                # Add topics if available
                if "content_analysis" in metadata:
                    topics = metadata["content_analysis"].get("key_topics", [])
                    chunk_metadata["topics"] = json.dumps(topics[:5])  # Limit to top 5
                
                metadatas.append(chunk_metadata)
                documents.append(chunk)
            
            # Add to collection
            if ids:
                collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
                total_chunks += len(ids)
        
        return {
            "success": True,
            "total_chunks": total_chunks,
            "total_documents": len(vectors_data),
            "collection": "redact_export",
            "path": os.path.join(EXPORT_DIR, "chromadb")
        }
    
    def export_single_document(self, document_id: str, filename: str = None) -> Dict:
        """Export a single document's metadata and vectors"""
        
        print(f"\nExporting single document: {document_id}")
        
        # Get metadata
        metadata_response = self.make_api_request(
            "/documents/extract-metadata",
            method="POST",
            data={
                "document_id": document_id,
                "filename": filename or "unknown",
                "extraction_types": ["all"]
            }
        )
        
        if not metadata_response.get("success"):
            return {"error": "Failed to extract metadata"}
        
        metadata = metadata_response["metadata"]
        
        # Get vectors
        vectors_response = self.make_api_request(
            "/documents/prepare-vectors",
            method="POST",
            data={
                "document_id": document_id,
                "filename": filename or "unknown",
                "chunk_size": CHUNK_SIZE,
                "overlap": CHUNK_OVERLAP,
                "strategy": "semantic"
            }
        )
        
        if not vectors_response.get("success"):
            return {"error": "Failed to prepare vectors"}
        
        chunks = vectors_response["chunks"]
        
        # Save to file
        output = {
            "document_id": document_id,
            "filename": filename or metadata.get("filename", "unknown"),
            "export_date": datetime.now().isoformat(),
            "metadata": metadata,
            "chunks": chunks,
            "chunk_settings": {
                "size": CHUNK_SIZE,
                "overlap": CHUNK_OVERLAP,
                "strategy": "semantic",
                "total_chunks": len(chunks)
            }
        }
        
        output_file = os.path.join(
            EXPORT_DIR, 
            f"document_{document_id.replace('/', '_')}.json"
        )
        
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"Exported to: {output_file}")
        
        return {
            "success": True,
            "output_file": output_file,
            "metadata_extracted": True,
            "chunks_created": len(chunks)
        }
    
    def create_rag_ready_export(self) -> Dict:
        """
        Create a complete export ready for RAG systems
        Includes metadata, vectors, and relationship mappings
        """
        print("\n" + "="*60)
        print("Creating RAG-Ready Export")
        print("="*60)
        
        documents = self.get_all_documents()
        if not documents:
            return {"error": "No documents found"}
        
        rag_export = {
            "export_metadata": {
                "created": datetime.now().isoformat(),
                "source": "Redact Document Processing System",
                "version": "1.0",
                "total_documents": len(documents),
                "chunk_settings": {
                    "size": CHUNK_SIZE,
                    "overlap": CHUNK_OVERLAP,
                    "strategy": "semantic"
                }
            },
            "documents": [],
            "index_mapping": {},  # Document ID to array index
            "entity_index": {},   # Entity to document IDs
            "topic_index": {}     # Topic to document IDs
        }
        
        for i, doc in enumerate(documents):
            print(f"\nProcessing {i+1}/{len(documents)}: {doc.get('filename', 'unknown')}")
            
            doc_id = doc.get("id") or doc.get("key")
            
            # Get metadata
            metadata = self.extract_metadata_for_document(doc)
            
            # Get chunks
            chunks = self.prepare_vectors_for_document(doc)
            
            if metadata and chunks:
                doc_export = {
                    "id": doc_id,
                    "filename": doc.get("filename", "unknown"),
                    "metadata": metadata,
                    "chunks": chunks,
                    "statistics": {
                        "total_chunks": len(chunks),
                        "entities_found": len(metadata.get("entities", {})),
                        "topics_found": len(metadata.get("content_analysis", {}).get("key_topics", []))
                    }
                }
                
                rag_export["documents"].append(doc_export)
                rag_export["index_mapping"][doc_id] = i
                
                # Build entity index
                if "entities" in metadata:
                    for entity_type, entities in metadata["entities"].items():
                        if entity_type not in rag_export["entity_index"]:
                            rag_export["entity_index"][entity_type] = {}
                        for entity in entities:
                            if entity not in rag_export["entity_index"][entity_type]:
                                rag_export["entity_index"][entity_type][entity] = []
                            rag_export["entity_index"][entity_type][entity].append(doc_id)
                
                # Build topic index
                if "content_analysis" in metadata:
                    for topic in metadata["content_analysis"].get("key_topics", []):
                        if topic not in rag_export["topic_index"]:
                            rag_export["topic_index"][topic] = []
                        rag_export["topic_index"][topic].append(doc_id)
            
            time.sleep(0.5)  # Rate limiting
        
        # Save RAG export
        output_file = os.path.join(
            EXPORT_DIR,
            f"rag_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(output_file, "w") as f:
            json.dump(rag_export, f, indent=2)
        
        print(f"\n✅ RAG export completed: {output_file}")
        print(f"   Documents: {len(rag_export['documents'])}")
        print(f"   Entity types: {len(rag_export['entity_index'])}")
        print(f"   Topics indexed: {len(rag_export['topic_index'])}")
        
        return {
            "success": True,
            "output_file": output_file,
            "documents_exported": len(rag_export["documents"]),
            "entity_types": list(rag_export["entity_index"].keys()),
            "topics_indexed": len(rag_export["topic_index"])
        }


def main():
    """Main export workflow"""
    
    print("\n" + "="*60)
    print("Redact Metadata & Vector Export Tool")
    print("="*60)
    
    # Check for auth token
    if AUTH_TOKEN == "YOUR_COGNITO_ID_TOKEN":
        print("\n⚠️  Please set your auth token first!")
        print("1. Log into https://redact.9thcube.com")
        print("2. Open DevTools > Network tab")
        print("3. Copy the Authorization token")
        print("4. Set environment variable: export REDACT_AUTH_TOKEN='your_token'")
        return
    
    exporter = RedactExporter()
    
    print("\nExport Options:")
    print("1. Export all metadata to JSON")
    print("2. Export all data to ChromaDB")
    print("3. Export both JSON and ChromaDB")
    print("4. Create RAG-ready export")
    print("5. Export single document")
    
    choice = input("\nSelect option (1-5): ").strip()
    
    if choice == "1":
        result = exporter.export_all_metadata("json")
    elif choice == "2":
        result = exporter.export_all_metadata("chromadb")
    elif choice == "3":
        result = exporter.export_all_metadata("both")
    elif choice == "4":
        result = exporter.create_rag_ready_export()
    elif choice == "5":
        doc_id = input("Enter document ID: ").strip()
        result = exporter.export_single_document(doc_id)
    else:
        print("Invalid option")
        return
    
    print("\n" + "="*60)
    print("Export Complete!")
    print(json.dumps(result, indent=2))
    print("="*60)


if __name__ == "__main__":
    main()