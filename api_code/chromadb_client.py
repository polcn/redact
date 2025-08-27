"""
ChromaDB integration for vector storage and retrieval
"""

import chromadb
from chromadb.config import Settings
import logging
import hashlib
import json
from typing import List, Dict, Optional, Any
import os

logger = logging.getLogger(__name__)

class ChromaDBClient:
    """Client for interacting with ChromaDB for vector storage and retrieval"""
    
    def __init__(self, persist_directory: str = "/tmp/chromadb", collection_name: str = "redact_documents"):
        """
        Initialize ChromaDB client
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection to use
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"Using existing collection: {collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
            logger.info(f"Created new collection: {collection_name}")
    
    def generate_document_id(self, user_id: str, document_id: str, chunk_index: int = 0) -> str:
        """
        Generate a unique ID for a document chunk
        
        Args:
            user_id: User ID who owns the document
            document_id: Original document ID
            chunk_index: Index of the chunk (for multi-chunk documents)
        
        Returns:
            Unique ID for the chunk
        """
        combined = f"{user_id}:{document_id}:{chunk_index}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    def store_vectors(
        self, 
        user_id: str,
        document_id: str,
        chunks: List[str],
        metadata: Dict[str, Any],
        embeddings: Optional[List[List[float]]] = None
    ) -> Dict[str, Any]:
        """
        Store document chunks and their vectors in ChromaDB
        
        Args:
            user_id: User ID who owns the document
            document_id: Original document ID
            chunks: List of text chunks
            metadata: Document metadata
            embeddings: Optional pre-computed embeddings (if not provided, ChromaDB will compute them)
        
        Returns:
            Dictionary with storage status and details
        """
        try:
            ids = []
            metadatas = []
            
            # Prepare data for each chunk
            for i, chunk in enumerate(chunks):
                chunk_id = self.generate_document_id(user_id, document_id, i)
                ids.append(chunk_id)
                
                # Create metadata for each chunk
                chunk_metadata = {
                    "user_id": user_id,
                    "document_id": document_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "filename": metadata.get("filename", "unknown"),
                    "content_type": metadata.get("content_type", "text/plain"),
                    "created_date": metadata.get("created_date", ""),
                    "chunk_size": len(chunk)
                }
                
                # Add extracted entities if available
                if "entities" in metadata:
                    chunk_metadata["entities"] = json.dumps(metadata["entities"])
                
                # Add topics if available
                if "content_analysis" in metadata and "key_topics" in metadata["content_analysis"]:
                    chunk_metadata["topics"] = json.dumps(metadata["content_analysis"]["key_topics"])
                
                metadatas.append(chunk_metadata)
            
            # Store in ChromaDB
            if embeddings:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=chunks,
                    metadatas=metadatas
                )
            else:
                # Let ChromaDB compute embeddings using its default model
                self.collection.add(
                    ids=ids,
                    documents=chunks,
                    metadatas=metadatas
                )
            
            logger.info(f"Stored {len(chunks)} chunks for document {document_id} (user: {user_id})")
            
            return {
                "success": True,
                "chunks_stored": len(chunks),
                "collection": self.collection_name,
                "document_id": document_id,
                "chunk_ids": ids
            }
            
        except Exception as e:
            logger.error(f"Error storing vectors: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def search_similar(
        self,
        user_id: str,
        query_text: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for similar documents/chunks
        
        Args:
            user_id: User ID to filter results (ensures user only searches their own documents)
            query_text: Text to search for
            n_results: Number of results to return
            filter_metadata: Additional metadata filters
        
        Returns:
            Dictionary with search results
        """
        try:
            # Build where clause to filter by user_id
            where_conditions = [{"user_id": {"$eq": user_id}}]
            
            # Add additional filters if provided
            if filter_metadata:
                if "filename" in filter_metadata:
                    where_conditions.append({"filename": {"$eq": filter_metadata["filename"]}})
                if "content_type" in filter_metadata:
                    where_conditions.append({"content_type": {"$eq": filter_metadata["content_type"]}})
            
            # Create final where clause
            if len(where_conditions) == 1:
                where_clause = where_conditions[0]
            else:
                where_clause = {"$and": where_conditions}
            
            # Perform search
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_clause
            )
            
            # Format results
            formatted_results = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    result = {
                        "chunk_id": results["ids"][0][i],
                        "text": results["documents"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else None,
                        "metadata": results["metadatas"][0][i]
                    }
                    formatted_results.append(result)
            
            logger.info(f"Found {len(formatted_results)} similar chunks for user {user_id}")
            
            return {
                "success": True,
                "query": query_text,
                "results": formatted_results,
                "total_results": len(formatted_results)
            }
            
        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
    
    def delete_document_vectors(self, user_id: str, document_id: str) -> Dict[str, Any]:
        """
        Delete all vectors associated with a document
        
        Args:
            user_id: User ID who owns the document
            document_id: Document ID to delete
        
        Returns:
            Dictionary with deletion status
        """
        try:
            # Get all chunks for this document using AND operator
            results = self.collection.get(
                where={"$and": [
                    {"user_id": {"$eq": user_id}},
                    {"document_id": {"$eq": document_id}}
                ]}
            )
            
            if results["ids"]:
                # Delete the chunks
                self.collection.delete(
                    ids=results["ids"]
                )
                
                logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
                
                return {
                    "success": True,
                    "chunks_deleted": len(results["ids"]),
                    "document_id": document_id
                }
            else:
                return {
                    "success": True,
                    "chunks_deleted": 0,
                    "document_id": document_id,
                    "message": "No chunks found for document"
                }
                
        except Exception as e:
            logger.error(f"Error deleting vectors: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics about a user's stored vectors
        
        Args:
            user_id: User ID to get statistics for
        
        Returns:
            Dictionary with user statistics
        """
        try:
            # Get all documents for user
            results = self.collection.get(
                where={"user_id": {"$eq": user_id}}
            )
            
            if not results["ids"]:
                return {
                    "success": True,
                    "total_chunks": 0,
                    "unique_documents": 0,
                    "total_size": 0
                }
            
            # Calculate statistics
            unique_docs = set()
            total_size = 0
            
            for metadata in results["metadatas"]:
                unique_docs.add(metadata.get("document_id"))
                total_size += metadata.get("chunk_size", 0)
            
            return {
                "success": True,
                "total_chunks": len(results["ids"]),
                "unique_documents": len(unique_docs),
                "total_size": total_size,
                "documents": list(unique_docs)
            }
            
        except Exception as e:
            logger.error(f"Error getting user statistics: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def reset_collection(self):
        """Reset the collection (delete all data) - USE WITH CAUTION"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Reset collection: {self.collection_name}")
            return {"success": True, "message": "Collection reset successfully"}
        except Exception as e:
            logger.error(f"Error resetting collection: {str(e)}")
            return {"success": False, "error": str(e)}


# Singleton instance for Lambda
_chromadb_client = None

def get_chromadb_client() -> ChromaDBClient:
    """Get or create ChromaDB client singleton"""
    global _chromadb_client
    if _chromadb_client is None:
        # Use EFS mount point if available, otherwise use /tmp
        persist_dir = os.environ.get("CHROMADB_PERSIST_DIR", "/tmp/chromadb")
        collection_name = os.environ.get("CHROMADB_COLLECTION", "redact_documents")
        _chromadb_client = ChromaDBClient(persist_dir, collection_name)
    return _chromadb_client