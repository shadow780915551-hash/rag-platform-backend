# RAG Platform

A production-ready Retrieval Augmented Generation (RAG) platform built with FastAPI, featuring advanced AI capabilities for document processing, semantic search, and intelligent chat interactions.

## Features

### Core Features
- **PDF Upload & Processing**: Upload multiple PDF documents with automatic text extraction and chunking
- **Semantic Search**: Advanced semantic search using Sentence Transformers and FAISS vector indexing
- **Hybrid Search**: Combine semantic search with keyword-based approaches for better results
- **Cross-Encoder Re-ranking**: Improve search relevance with cross-encoder re-ranking
- **Query Expansion**: Expand queries using synonyms and NLP techniques
- **Conversation Memory**: Maintain context across multi-turn conversations
- **Source Citations**: Provide source citations for all responses
- **Multi-PDF Support**: Search across multiple documents simultaneously

### Authentication & Security
- **JWT Authentication**: Secure token-based authentication
- **Role-Based Access Control (RBAC)**: Admin, User, and Guest roles
- **Password Hashing**: Bcrypt-based password hashing
- **Protected Endpoints**: Secure API endpoints with middleware

### AI/ML Capabilities
- **Sentence Transformers**: State-of-the-art text embeddings
- **FAISS Vector Store**: Efficient similarity search
- **Cross-Encoder Models**: Advanced re-ranking
- **Chunk Overlap Optimization**: Intelligent text chunking with overlap
- **Query Expansion**: Synonym-based query enhancement

### Admin Dashboard
- **System Statistics**: View platform-wide metrics
- **User Management**: Manage user accounts
- **Document Management**: Monitor document processing
- **Storage Usage**: Track storage consumption
- **Health Monitoring**: System health checks

### Technical Features
- **Async APIs**: Fast async/await patterns
- **Background Tasks**: Celery for async processing
- **Logging**: Comprehensive logging with Loguru
- **Docker Support**: Full containerization
- **Docker Compose**: Multi-container orchestration
- **CI/CD Pipeline**: GitHub Actions automation
- **API Documentation**: Auto-generated Swagger/OpenAPI docs

## Architecture

```
rag-platform/
├── app/
│   ├── core/           # Configuration and settings
│   ├── database/       # Database connection and models
│   ├── middlewares/    # Custom middleware
│   ├── models/         # SQLAlchemy models
│   ├── routers/        # API route handlers
│   ├── services/       # Business logic services
│   └── utils/          # Utility functions
├── data/
│   ├── uploads/        # Uploaded PDF files
│   └── vector_stores/  # FAISS index files
├── tests/              # Test suite
├── docs/               # Documentation
├── Dockerfile          # Docker image definition
├── docker-compose.yml  # Multi-container setup
└── requirements.txt    # Python dependencies
```

## Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework
- **SQLAlchemy**: ORM for database operations
- **PostgreSQL/SQLite**: Database options
- **Celery**: Distributed task queue
- **Redis**: Message broker and cache

### AI/ML
- **Sentence Transformers**: Text embeddings
- **FAISS**: Vector similarity search
- **Cross-Encoder**: Re-ranking models
- **NLTK**: Natural language processing
- **PyPDF2/pdfplumber**: PDF processing

### DevOps
- **Docker**: Containerization
- **Docker Compose**: Container orchestration
- **GitHub Actions**: CI/CD pipeline
- **Render**: Cloud deployment option

## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL (optional, for production)
- Redis (for Celery)
- Docker and Docker Compose (for containerized deployment)

### Local Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/rag-platform.git
cd rag-platform
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Download NLTK data**
```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('wordnet'); nltk.download('stopwords')"
```

5. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

6. **Initialize database**
```bash
python -c "from app.database.connection import init_db; init_db()"
```

7. **Run the application**
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Docker Deployment

1. **Build and run with Docker Compose**
```bash
docker-compose up -d
```

2. **View logs**
```bash
docker-compose logs -f
```

3. **Stop services**
```bash
docker-compose down
```

## API Documentation

Once the application is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### Authentication Endpoints

#### Register User
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "securepassword",
  "role": "user"
}
```

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword
```

#### Get Current User
```http
GET /api/v1/auth/me
Authorization: Bearer <token>
```

### Document Endpoints

#### Upload PDF
```http
POST /api/v1/documents/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <pdf_file>
title: "Document Title"
description: "Optional description"
```

#### List Documents
```http
GET /api/v1/documents/?skip=0&limit=20
Authorization: Bearer <token>
```

#### Get Document
```http
GET /api/v1/documents/{document_id}
Authorization: Bearer <token>
```

#### Delete Document
```http
DELETE /api/v1/documents/{document_id}
Authorization: Bearer <token>
```

#### Download Document
```http
GET /api/v1/documents/{document_id}/download
Authorization: Bearer <token>
```

### Chat Endpoints

#### Chat Query
```http
POST /api/v1/chat/query
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "What is the main topic of the document?",
  "document_id": 1,
  "conversation_id": null,
  "use_reranking": true,
  "use_query_expansion": true
}
```

#### List Conversations
```http
GET /api/v1/chat/conversations?skip=0&limit=20
Authorization: Bearer <token>
```

#### Get Conversation Messages
```http
GET /api/v1/chat/conversations/{conversation_id}/messages
Authorization: Bearer <token>
```

#### Export Conversation
```http
GET /api/v1/chat/conversations/{conversation_id}/export
Authorization: Bearer <token>
```

#### Delete Conversation
```http
DELETE /api/v1/chat/conversations/{conversation_id}
Authorization: Bearer <token>
```

### Admin Endpoints

#### Get System Stats
```http
GET /api/v1/admin/stats
Authorization: Bearer <admin_token>
```

#### Get User Stats
```http
GET /api/v1/admin/users/stats?skip=0&limit=50
Authorization: Bearer <admin_token>
```

#### Get Document Stats
```http
GET /api/v1/admin/documents/stats?skip=0&limit=50
Authorization: Bearer <admin_token>
```

#### Get Storage Usage
```http
GET /api/v1/admin/storage/usage
Authorization: Bearer <admin_token>
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | RAG Platform |
| `APP_VERSION` | Application version | 1.0.0 |
| `DEBUG` | Debug mode | True |
| `SECRET_KEY` | JWT secret key | (change in production) |
| `DATABASE_URL` | Database connection string | sqlite:///./rag_platform.db |
| `EMBEDDING_MODEL` | Sentence transformer model | sentence-transformers/all-MiniLM-L6-v2 |
| `CROSS_ENCODER_MODEL` | Cross-encoder model | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| `CHUNK_SIZE` | Text chunk size | 512 |
| `CHUNK_OVERLAP` | Chunk overlap | 50 |
| `MAX_RESULTS` | Max search results | 10 |
| `RERANK_TOP_K` | Re-rank top K results | 5 |
| `VECTOR_STORE_PATH` | Vector store directory | ./data/vector_stores |
| `UPLOAD_DIR` | Upload directory | ./data/uploads |
| `MAX_FILE_SIZE` | Max file size (bytes) | 10485760 |
| `REDIS_URL` | Redis connection | redis://localhost:6379/0 |
| `LOG_LEVEL` | Logging level | INFO |
| `LOG_FILE` | Log file path | ./logs/app.log |
| `CORS_ORIGINS` | CORS allowed origins | http://localhost:3000,http://localhost:8000 |

## Development

### Running Tests
```bash
pytest tests/ -v --cov=app
```

### Code Formatting
```bash
black app/
```

### Linting
```bash
flake8 app/
```

### Type Checking
```bash
mypy app/
```

## Deployment

### Render Deployment

1. **Create a Render account** at [render.com](https://render.com)

2. **Create a new web service**
   - Connect your GitHub repository
   - Select "Docker" as the runtime
   - Configure environment variables
   - Deploy

3. **Add PostgreSQL database**
   - Create a PostgreSQL instance
   - Update `DATABASE_URL` environment variable

4. **Add Redis instance**
   - Create a Redis instance
   - Update `REDIS_URL` environment variable

### Docker Deployment

1. **Build the image**
```bash
docker build -t rag-platform .
```

2. **Run the container**
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host/db \
  -e SECRET_KEY=your-secret-key \
  rag-platform
```

## Monitoring

### Flower (Celery Monitoring)
Access Flower at `http://localhost:5555` to monitor Celery tasks.

### Logs
Logs are stored in the `./logs` directory:
- `app.log`: General application logs
- `app_error.log`: Error logs only

## Performance Optimization

### Vector Store Optimization
- Use IVF or HNSW indexes for large document collections
- Adjust `nlist` parameter for IVF index based on data size
- Consider GPU acceleration for embedding generation

### Database Optimization
- Use PostgreSQL for production deployments
- Add indexes on frequently queried columns
- Enable connection pooling

### Caching
- Redis is used for Celery task queue
- Consider caching frequently accessed data
- Implement response caching for expensive operations

## Security Considerations

1. **Always change the default `SECRET_KEY` in production**
2. **Use HTTPS in production**
3. **Implement rate limiting**
4. **Regular security updates**
5. **Input validation and sanitization**
6. **Secure file upload handling**
7. **Database connection encryption**
8. **Regular backups**

## Troubleshooting

### Common Issues

**PDF Processing Fails**
- Ensure PDF files are not corrupted
- Check file size limits
- Verify pdfplumber/PyPDF2 installation

**Memory Issues**
- Reduce `CHUNK_SIZE` for large documents
- Process documents in batches
- Increase system memory

**Slow Search Performance**
- Use appropriate FAISS index type
- Consider re-ranking only top results
- Implement result caching

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Open an issue on GitHub
- Check the documentation
- Review the API docs at `/docs`

## Roadmap

- [ ] Add support for more document formats (DOCX, TXT, etc.)
- [ ] Implement advanced LLM integration (GPT-4, Claude)
- [ ] Add multi-language support
- [ ] Implement document versioning
- [ ] Add collaborative features
- [ ] Implement advanced analytics
- [ ] Add webhooks integration
- [ ] Create mobile API
