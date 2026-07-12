"""
Background Tasks Module

This module handles background task processing using Celery for async operations.
"""

from celery import Celery
from app.core.config import get_settings
from loguru import logger

settings = get_settings()

# Create Celery application
celery_app = Celery(
    "rag_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)


@celery_app.task(bind=True)
def process_document_task(self, document_id: int, file_path: str):
    """
    Background task to process a document.
    
    Args:
        document_id: Document ID
        file_path: Path to PDF file
    """
    from app.database.connection import SessionLocal
    from app.models.document import Document
    from app.models.chunk import DocumentChunk
    from app.services.pdf_processor import get_pdf_processor
    from app.services.embedding import get_embedding_service
    from app.services.vector_store import get_vector_store
    from datetime import datetime
    import os
    
    db = SessionLocal()
    
    try:
        logger.info(f"Processing document {document_id} in background")
        
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"Document {document_id} not found")
            return {"status": "error", "message": "Document not found"}
        
        # Update task status
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100, "status": "Extracting text"})
        
        # Process PDF
        pdf_processor = get_pdf_processor()
        chunks = pdf_processor.process_pdf(file_path)
        
        if not chunks:
            logger.warning(f"No chunks generated for document {document_id}")
            document.is_processed = 1
            db.commit()
            return {"status": "warning", "message": "No text extracted"}
        
        self.update_state(state="PROGRESS", meta={"current": 30, "total": 100, "status": "Generating embeddings"})
        
        # Generate embeddings
        embedding_service = get_embedding_service()
        texts = [chunk["text"] for chunk in chunks]
        embeddings = embedding_service.encode_text(texts)
        
        self.update_state(state="PROGRESS", meta={"current": 60, "total": 100, "status": "Storing chunks"})
        
        # Store chunks in database
        chunk_records = []
        for i, chunk in enumerate(chunks):
            chunk_record = DocumentChunk(
                document_id=document_id,
                chunk_text=chunk["text"],
                page_number=chunk["page_number"],
                chunk_index=chunk["chunk_index"],
                chunk_metadata=str(chunk)
            )
            chunk_records.append(chunk_record)
        
        db.add_all(chunk_records)
        db.commit()
        
        self.update_state(state="PROGRESS", meta={"current": 80, "total": 100, "status": "Building vector index"})
        
        # Create vector store
        dimension = embedding_service.get_embedding_dimension()
        vector_store = get_vector_store(document_id, dimension)
        
        # Add embeddings to vector store
        document_ids = [chunk.id for chunk in chunk_records]
        vector_store.add_vectors(embeddings, document_ids)
        
        # Save vector store
        vector_store_path = os.path.join(
            settings.VECTOR_STORE_PATH,
            f"document_{document_id}.index"
        )
        os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)
        vector_store.save_index(vector_store_path)
        
        self.update_state(state="PROGRESS", meta={"current": 100, "total": 100, "status": "Completed"})
        
        # Update document status
        document.is_processed = 1
        document.processed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Successfully processed document {document_id}")
        return {"status": "success", "document_id": document_id, "chunks_count": len(chunks)}
    
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        db.rollback()
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()


@celery_app.task
def cleanup_old_files_task():
    """
    Background task to cleanup old files and temporary data.
    """
    import os
    from datetime import datetime, timedelta
    from app.database.connection import SessionLocal
    from app.models.document import Document
    
    db = SessionLocal()
    
    try:
        logger.info("Running cleanup task")
        
        # Find documents older than 30 days that are marked for deletion
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # This is a placeholder for cleanup logic
        # In production, implement actual cleanup based on your requirements
        
        logger.info("Cleanup task completed")
        return {"status": "success"}
    
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()


@celery_app.task
def health_check_task():
    """
    Background task for periodic health checks.
    """
    try:
        logger.info("Running health check")
        
        # Check database connection
        from app.database.connection import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        
        # Check Redis connection
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        
        logger.info("Health check passed")
        return {"status": "healthy"}
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}
