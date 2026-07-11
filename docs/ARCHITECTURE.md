# RAG Platform Architecture

## System Architecture Overview

The RAG Platform follows a microservices-inspired architecture with clear separation of concerns, enabling scalability and maintainability.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Web UI     │  │  Mobile App  │  │  API Client  │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼────────────────┼────────────────┼──────────────────┘
          │                │                │
          └────────────────┼────────────────┘
                           │
┌──────────────────────────┼────────────────────────────────────┐
│                   API Gateway / Load Balancer                 │
└──────────────────────────┼────────────────────────────────────┘
                           │
┌──────────────────────────┼────────────────────────────────────┐
│                      FastAPI Application                      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Middleware Layer                            │  │
│  │  • CORS • Authentication • RBAC • Logging               │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Router Layer                               │  │
│  │  • Auth • Documents • Chat • Admin                     │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Service Layer                               │  │
│  │  • Embedding • Vector Store • PDF Processor             │  │
│  │  • Re-ranking • Query Expansion • Conversation Memory   │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────┼────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
┌─────────┼────────┐  ┌─────┼──────┐  ┌─────┼──────┐
│  PostgreSQL  │  │   Redis   │  │  File Storage│
│  (Database)  │  │  (Cache)   │  │  (PDFs/FAISS)│
└──────────────┘  └────────────┘  └──────────────┘
                           │
┌──────────────────────────┼────────────────────────────────────┐
│                    Background Processing                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Celery Worker                               │  │
│  │  • Document Processing • Embedding Generation            │  │
│  │  • Vector Index Building • Cleanup Tasks                 │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Celery Beat                                 │  │
│  │  • Scheduled Tasks • Health Checks • Maintenance         │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. API Layer (FastAPI)

**Responsibilities:**
- HTTP request/response handling
- Request validation
- Authentication and authorization
- Response formatting
- API documentation (Swagger/OpenAPI)

**Key Components:**
- **Routers**: Organized by domain (auth, documents, chat, admin)
- **Middleware**: Authentication, RBAC, CORS, logging
- **Pydantic Models**: Request/response validation

### 2. Service Layer

**Embedding Service**
- Manages Sentence Transformer models
- Generates text embeddings
- Caches model instances
- Handles batch processing

**Vector Store Service**
- Manages FAISS indexes
- Supports multiple index types (Flat, IVF, HNSW)
- Handles vector addition and search
- Persists indexes to disk

**PDF Processor Service**
- Extracts text from PDFs
- Implements chunk overlap optimization
- Cleans and normalizes text
- Extracts document metadata

**Re-ranking Service**
- Uses Cross-Encoder models
- Re-ranks search results
- Improves result relevance
- Supports batch processing

**Query Expansion Service**
- Expands queries with synonyms
- Implements lemmatization
- Generates query variations
- Uses WordNet for synonyms

**Conversation Memory Service**
- Manages conversation history
- Stores and retrieves messages
- Maintains context
- Handles citations

### 3. Data Layer

**PostgreSQL Database**
- User accounts and authentication
- Document metadata
- Conversation history
- Message storage
- Document chunks

**Redis**
- Celery task queue
- Result backend
- Session caching
- Rate limiting (optional)

**File Storage**
- Uploaded PDF files
- FAISS vector indexes
- Index metadata
- Log files

### 4. Background Processing

**Celery Worker**
- Processes documents asynchronously
- Generates embeddings
- Builds vector indexes
- Handles long-running tasks

**Celery Beat**
- Scheduled maintenance tasks
- Health checks
- Cleanup operations
- Periodic data synchronization

**Flower**
- Celery task monitoring
- Task status tracking
- Performance metrics
- Worker management

## Data Flow

### Document Upload Flow

```
1. Client uploads PDF
   ↓
2. FastAPI validates and stores file
   ↓
3. Document record created in DB
   ↓
4. Celery task queued for processing
   ↓
5. Worker extracts text from PDF
   ↓
6. Text chunked with overlap
   ↓
7. Embeddings generated
   ↓
8. Chunks stored in DB
   ↓
9. Vector index built
   ↓
10. Index saved to disk
    ↓
11. Document marked as processed
```

### Chat Query Flow

```
1. Client submits query
   ↓
2. Query expanded (optional)
   ↓
3. Query embedding generated
   ↓
4. Vector search performed
   ↓
5. Results re-ranked (optional)
   ↓
6. Relevant chunks retrieved
   ↓
7. Answer generated
   ↓
8. Citations prepared
   ↓
9. Response returned to client
   ↓
10. Conversation updated
```

## Security Architecture

### Authentication Flow

```
1. User registers/logs in
   ↓
2. Credentials validated
   ↓
3. JWT token generated
   ↓
4. Token returned to client
   ↓
5. Client includes token in requests
   ↓
6. Middleware validates token
   ↓
7. User context attached to request
   ↓
8. RBAC checks performed
   ↓
9. Request processed or denied
```

### Security Layers

1. **Transport Layer**: HTTPS/TLS encryption
2. **Authentication**: JWT token validation
3. **Authorization**: Role-based access control
4. **Input Validation**: Pydantic model validation
5. **SQL Injection Prevention**: ORM parameterized queries
6. **File Upload Security**: Type and size validation
7. **Rate Limiting**: Redis-based rate limiting (optional)
8. **CORS**: Configured allowed origins

## Scalability Considerations

### Horizontal Scaling

**API Servers**
- Stateless design enables horizontal scaling
- Load balancer distributes requests
- Shared database and Redis

**Celery Workers**
- Scale workers independently
- Task queue distributes load
- Worker autoscaling based on queue length

**Database**
- Read replicas for query scaling
- Connection pooling
- Query optimization

### Vertical Scaling

**Memory**
- Increase memory for large document processing
- Optimize chunk size based on available memory
- Implement streaming for large files

**CPU**
- Multi-core utilization for embedding generation
- Parallel processing support
- GPU acceleration for AI models

### Caching Strategy

**Model Caching**
- Embedding models cached in memory
- Cross-encoder models cached
- Reduced model loading overhead

**Result Caching**
- Cache frequent search results
- TTL-based expiration
- Invalidation on document updates

**Session Caching**
- Redis session storage
- Fast session retrieval
- Distributed session support

## Deployment Architecture

### Development Environment

```
Local Machine
├── FastAPI (uvicorn)
├── SQLite Database
├── File System Storage
└── Optional: Redis (for Celery)
```

### Production Environment

```
┌─────────────────────────────────────────┐
│           Load Balancer                 │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───┴───┐   ┌───┴───┐   ┌───┴───┐
│ API 1 │   │ API 2 │   │ API N │
└───┬───┘   └───┬───┘   └───┬───┘
    │            │            │
    └────────────┼────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───┴──────┐ ┌───┴──────┐ ┌───┴──────┐
│PostgreSQL│ │  Redis   │ │  Storage │
│ (Primary)│ │ (Cluster)│ │  (S3/NFS)│
└──────────┘ └──────────┘ └──────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───┴──────┐ ┌───┴──────┐ ┌───┴──────┐
│Worker 1  │ │Worker 2  │ │Worker N  │
└──────────┘ └──────────┘ └──────────┘
```

## Monitoring and Observability

### Logging

**Application Logs**
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Log rotation and retention
- Centralized log aggregation

**Error Logs**
- Separate error log file
- Stack traces included
- Error context captured
- Alert integration

### Metrics

**Application Metrics**
- Request/response times
- Error rates
- Active connections
- Document processing times

**System Metrics**
- CPU usage
- Memory usage
- Disk I/O
- Network traffic

**Business Metrics**
- User registrations
- Document uploads
- Chat queries
- Search latency

### Health Checks

**Application Health**
- Database connectivity
- Redis connectivity
- File system accessibility
- Model loading status

**Service Health**
- API endpoint availability
- Celery worker status
- Task queue length
- Background task status

## Technology Rationale

### FastAPI
- Modern async support
- Automatic API documentation
- High performance
- Type hints and validation
- Growing ecosystem

### SQLAlchemy
- Powerful ORM
- Database agnostic
- Migration support
- Query optimization
- Connection pooling

### Celery
- Distributed task queue
- Reliable task execution
- Monitoring with Flower
- Scheduled tasks
- Result backend

### Sentence Transformers
- State-of-the-art embeddings
- Pre-trained models
- Multi-language support
- Easy integration
- Good performance

### FAISS
- Efficient similarity search
- Multiple index types
- Scalable to billions of vectors
- GPU support
- Facebook/Meta support

### PostgreSQL
- ACID compliance
- Advanced features
- Scalability
- Strong community
- Cloud support

## Future Enhancements

### Planned Improvements

1. **LLM Integration**
   - GPT-4 for answer generation
   - Claude API integration
   - Local LLM support (Llama, Mistral)

2. **Advanced Search**
   - Hybrid search with BM25
   - Multi-modal search (text + images)
   - Faceted search
   - Search analytics

3. **Document Processing**
   - Support for more formats
   - OCR for scanned PDFs
   - Table extraction
   - Image processing

4. **Collaboration Features**
   - Document sharing
   - Team workspaces
   - Comments and annotations
   - Version control

5. **Analytics**
   - Usage analytics
   - Search analytics
   - User behavior tracking
   - Performance insights

6. **Security**
   - 2FA authentication
   - SSO integration
   - Advanced RBAC
   - Audit logging
