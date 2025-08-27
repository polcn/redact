# RAG Integration Guide - ChromaDB with Redact

## Overview
The Redact application now includes full support for RAG (Retrieval-Augmented Generation) workflows using ChromaDB for vector storage and search. This guide explains how to integrate the metadata extraction and vector storage features for your indexing and RAG needs.

## Architecture

```
Document Upload → Metadata Extraction → Vector Preparation → ChromaDB Storage → Vector Search → RAG Query
```

## Key Components

### 1. Metadata Extraction (`/documents/extract-metadata`)
Extracts comprehensive metadata from documents including:
- **Entities**: Names, locations, organizations, dates, monetary values
- **Topics**: Key topics and keywords
- **Structure**: Document structure analysis
- **Properties**: File properties and statistics

### 2. Vector Preparation (`/documents/prepare-vectors`)
Chunks documents into semantic segments for vector storage:
- **Chunking Strategies**: `semantic`, `structure`, `size`
- **Configurable**: Chunk size and overlap
- **Smart Splitting**: Preserves sentence boundaries

### 3. Vector Storage (`/vectors/store`)
Stores document chunks and embeddings in ChromaDB:
- **User Isolation**: Each user's vectors are isolated
- **Metadata Preservation**: Stores metadata with chunks
- **Automatic Embeddings**: ChromaDB generates embeddings if not provided

### 4. Vector Search (`/vectors/search`)
Semantic search across stored documents:
- **Similarity Search**: Find relevant chunks by query
- **Metadata Filtering**: Filter by filename, content type, etc.
- **User Scoped**: Only searches user's own documents

## API Endpoints

### Store Vectors
```http
POST /vectors/store
Authorization: Bearer {token}

{
  "document_id": "processed/users/{user_id}/document.pdf",
  "chunks": ["chunk1 text", "chunk2 text"],
  "metadata": {
    "filename": "document.pdf",
    "entities": {...},
    "content_analysis": {...}
  }
}
```

### Search Vectors
```http
POST /vectors/search
Authorization: Bearer {token}

{
  "query": "What are the privacy requirements?",
  "n_results": 5,
  "filter": {
    "filename": "privacy_policy.pdf"
  }
}
```

### Delete Vectors
```http
DELETE /vectors/delete?document_id={document_id}
Authorization: Bearer {token}
```

### Get Statistics
```http
GET /vectors/stats
Authorization: Bearer {token}
```

## Complete Workflow Example

### Step 1: Upload Document
```python
# Upload document via existing upload endpoint
response = upload_document("document.pdf", content)
document_id = response["document_id"]
```

### Step 2: Extract Metadata
```python
metadata = extract_metadata(
    document_id=document_id,
    extraction_types=["all"]
)
```

### Step 3: Prepare Vectors
```python
chunks = prepare_vectors(
    document_id=document_id,
    chunk_size=512,
    overlap=50,
    strategy="semantic"
)
```

### Step 4: Store in ChromaDB
```python
store_result = store_vectors(
    document_id=document_id,
    chunks=chunks["chunks"],
    metadata=metadata
)
```

### Step 5: Search for Similar Content
```python
results = search_vectors(
    query="privacy and security requirements",
    n_results=5
)
```

### Step 6: Use for RAG
```python
# Use retrieved chunks as context for AI generation
context = "\n".join([r["text"] for r in results])
answer = generate_ai_response(
    context=context,
    question="What are the main privacy requirements?"
)
```

## Python Example Script

See `rag_workflow_example.py` for a complete working example that demonstrates:
- Document processing pipeline
- Vector storage in ChromaDB
- Semantic search
- RAG query generation

## Lambda Deployment

### Adding ChromaDB to Lambda

1. **Install ChromaDB in Lambda layer**:
```bash
pip install chromadb -t python/
zip -r chromadb-layer.zip python/
aws lambda publish-layer-version \
  --layer-name chromadb \
  --zip-file fileb://chromadb-layer.zip
```

2. **Attach layer to Lambda**:
```bash
aws lambda update-function-configuration \
  --function-name redact-api-handler \
  --layers arn:aws:lambda:us-east-1:028358929215:layer:chromadb:1
```

3. **Configure environment variables**:
```bash
aws lambda update-function-configuration \
  --function-name redact-api-handler \
  --environment Variables={CHROMADB_PERSIST_DIR=/tmp/chromadb,CHROMADB_COLLECTION=redact_documents}
```

### Using EFS for Persistence (Recommended)

For production, mount an EFS filesystem to persist ChromaDB data:

1. **Create EFS filesystem**
2. **Mount to Lambda**:
```bash
aws lambda update-function-configuration \
  --function-name redact-api-handler \
  --file-system-configs Arn=arn:aws:elasticfilesystem:us-east-1:028358929215:access-point/fsap-xxx,LocalMountPath=/mnt/efs
```

3. **Update environment**:
```bash
CHROMADB_PERSIST_DIR=/mnt/efs/chromadb
```

## Frontend Integration

### Add Vector Storage Button
```typescript
// In FileItem component
const handleVectorize = async () => {
  // Extract metadata
  const metadata = await api.extractMetadata(file.id);
  
  // Prepare vectors
  const vectors = await api.prepareVectors(file.id);
  
  // Store in ChromaDB
  await api.storeVectors(file.id, vectors.chunks, metadata);
};
```

### Add Search Component
```typescript
// SearchComponent.tsx
const handleSearch = async (query: string) => {
  const results = await api.searchVectors(query, 5);
  setSearchResults(results);
};
```

## Configuration Options

### Chunking Strategies

1. **Semantic**: Smart chunking based on content structure
   - Best for: Documents with clear sections
   - Preserves: Paragraph boundaries

2. **Structure**: Based on document structure (headers, sections)
   - Best for: Structured documents (markdown, HTML)
   - Preserves: Document hierarchy

3. **Size**: Fixed-size chunks
   - Best for: Uniform processing
   - Preserves: Nothing special

### Chunk Size Recommendations

- **Small chunks (256-512 chars)**: Better for specific queries
- **Medium chunks (512-1024 chars)**: Balanced approach
- **Large chunks (1024-2048 chars)**: Better for context preservation

## Best Practices

1. **Always extract metadata first**: Provides valuable context for searches
2. **Use appropriate chunk sizes**: Depends on document type and use case
3. **Store original document ID**: Allows tracing back to source
4. **Implement user isolation**: Ensure users only access their own vectors
5. **Regular cleanup**: Delete vectors when documents are deleted
6. **Monitor storage**: Track vector database size and performance

## Troubleshooting

### Common Issues

1. **Import Error for ChromaDB**
   - Solution: Ensure chromadb is installed in Lambda layer

2. **Persistence Issues**
   - Solution: Use EFS for production persistence

3. **Memory Issues**
   - Solution: Increase Lambda memory to 512MB+

4. **Search Not Finding Results**
   - Check: User ID filtering is correct
   - Check: Documents were properly vectorized

## Next Steps

1. **Deploy Lambda Updates**:
```bash
./build_lambda.sh api
aws lambda update-function-code \
  --function-name redact-api-handler \
  --zip-file fileb://api_lambda.zip
```

2. **Update API Gateway** (if needed):
   - Add new endpoints to API Gateway
   - Configure CORS for new endpoints
   - Deploy API changes

3. **Test with Example Script**:
```bash
python3 rag_workflow_example.py
```

4. **Integrate with Frontend**:
   - Add vector storage UI
   - Implement search interface
   - Create RAG query component

## Support

For issues or questions:
- Check Lambda logs: `/aws/lambda/redact-api-handler`
- Review ChromaDB documentation: https://docs.trychroma.com
- Test with the example script first