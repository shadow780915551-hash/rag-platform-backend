"""
Documents Router Module

This module handles document upload, deletion, and management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import os
import shutil
import uuid
from datetime import datetime

from app.database.connection import get_db
from app.models.user import User
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.utils.auth import get_current_active_user
from app.services.pdf_processor import get_pdf_processor
from app.services.embedding import get_embedding_service
from app.services.vector_store import get_vector_store
from app.core.config import get_settings
from loguru import logger

settings = get_settings()

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


# Pydantic models
class DocumentResponse(BaseModel):
    """Document response model."""
    id: int
    filename: str
    file_size: int
    page_count: int
    title: Optional[str]
    description: Optional[str]
    uploaded_at: str
    processed_at: Optional[str]
    is_processed: bool


class DocumentListResponse(BaseModel):
    """Document list response model."""
    documents: List[DocumentResponse]
    total: int


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF document.
    
    Args:
        file: PDF file to upload
        title: Optional document title
        description: Optional document description
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        DocumentResponse: Uploaded document information
        
    Raises:
        HTTPException: If file is invalid or upload fails
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Validate file size
    file_content = await file.read()
    if len(file_content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum limit of {settings.MAX_FILE_SIZE} bytes"
        )
    
    # Create upload directory if it doesn't exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    # Save file
    try:
        with open(file_path, 'wb') as f:
            f.write(file_content)
        logger.info(f"File saved to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file"
        )
    
    # Get PDF metadata
    pdf_processor = get_pdf_processor()
    metadata = pdf_processor.get_document_metadata(file_path)
    
    # Create document record
    document = Document(
        filename=file.filename,
        file_path=file_path,
        file_size=len(file_content),
        page_count=metadata.get("page_count", 0),
        title=title or metadata.get("title", file.filename),
        description=description,
        user_id=current_user.id,
        is_processed=0
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Process document in background (async)
    # Note: In production, this should be handled by Celery
    try:
        process_document_async(document.id, file_path, db)
    except Exception as e:
        logger.error(f"Failed to process document: {e}")
    
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_size=document.file_size,
        page_count=document.page_count,
        title=document.title,
        description=document.description,
        uploaded_at=document.uploaded_at.isoformat(),
        processed_at=document.processed_at.isoformat() if document.processed_at else None,
        is_processed=bool(document.is_processed)
    )


def process_document_async(document_id: int, file_path: str, db: Session):
    """
    Process document asynchronously (extract text, chunk, embed).
    
    Args:
        document_id: Document ID
        file_path: Path to PDF file
        db: Database session
    """
    try:
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"Document {document_id} not found")
            return
        
        # Process PDF
        pdf_processor = get_pdf_processor()
        chunks = pdf_processor.process_pdf(file_path)
        
        if not chunks:
            logger.warning(f"No chunks generated for document {document_id}")
            document.is_processed = 1
            db.commit()
            return
        
        # Generate embeddings
        embedding_service = get_embedding_service()
        texts = [chunk["text"] for chunk in chunks]
        embeddings = embedding_service.encode_text(texts)
        
        # Store chunks in database
        chunk_records = []
        for i, chunk in enumerate(chunks):
            chunk_record = DocumentChunk(
                document_id=document_id,
                chunk_text=chunk["text"],
                page_number=chunk["page_number"],
                chunk_index=chunk["chunk_index"],
                metadata=str(chunk)
            )
            chunk_records.append(chunk_record)
        
        db.add_all(chunk_records)
        db.commit()
        
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
        
        # Update document status
        document.is_processed = 1
        document.processed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Successfully processed document {document_id}")
    
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        db.rollback()


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List user's documents.
    
    Args:
        skip: Number of documents to skip
        limit: Maximum number of documents to return
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        DocumentListResponse: List of documents
    """
    query = db.query(Document).filter(Document.user_id == current_user.id)
    total = query.count()
    documents = query.order_by(Document.uploaded_at.desc()).offset(skip).limit(limit).all()
    
    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                file_size=doc.file_size,
                page_count=doc.page_count,
                title=doc.title,
                description=doc.description,
                uploaded_at=doc.uploaded_at.isoformat(),
                processed_at=doc.processed_at.isoformat() if doc.processed_at else None,
                is_processed=bool(doc.is_processed)
            )
            for doc in documents
        ],
        total=total
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get document details.
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        DocumentResponse: Document information
        
    Raises:
        HTTPException: If document not found or access denied
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_size=document.file_size,
        page_count=document.page_count,
        title=document.title,
        description=document.description,
        uploaded_at=document.uploaded_at.isoformat(),
        processed_at=document.processed_at.isoformat() if document.processed_at else None,
        is_processed=bool(document.is_processed)
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a document.
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session
        
    Raises:
        HTTPException: If document not found or access denied
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete file
    try:
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete vector store
        vector_store_path = os.path.join(
            settings.VECTOR_STORE_PATH,
            f"document_{document_id}.index"
        )
        if os.path.exists(vector_store_path):
            os.remove(vector_store_path)
        
        metadata_path = vector_store_path.replace('.index', '_metadata.pkl')
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
    
    except Exception as e:
        logger.error(f"Failed to delete document files: {e}")
    
    # Delete from database (cascade will delete chunks)
    db.delete(document)
    db.commit()
    
    logger.info(f"Deleted document {document_id}")


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Download a document.
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        FileResponse: PDF file
        
    Raises:
        HTTPException: If document not found or access denied
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if not os.path.exists(document.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )
    
    return FileResponse(
        document.file_path,
        media_type="application/pdf",
        filename=document.filename
    )
