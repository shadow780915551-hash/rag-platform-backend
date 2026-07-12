"""
Admin Router Module

This module handles admin dashboard endpoints for system management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.models.conversation import Conversation
from app.models.message import Message
from app.utils.auth import get_current_admin_user
from loguru import logger

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# Pydantic models
class SystemStats(BaseModel):
    """System statistics model."""
    total_users: int
    total_documents: int
    total_chunks: int
    total_conversations: int
    total_messages: int
    active_users_last_24h: int


class UserStats(BaseModel):
    """User statistics model."""
    user_id: int
    username: str
    email: str
    document_count: int
    conversation_count: int
    message_count: int
    last_activity: Optional[str]


class DocumentStats(BaseModel):
    """Document statistics model."""
    document_id: int
    filename: str
    user_id: int
    username: str
    page_count: int
    chunk_count: int
    uploaded_at: str
    processed_at: Optional[str]


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get system-wide statistics.
    
    Args:
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        SystemStats: System statistics
    """
    # Count total users
    total_users = db.query(User).count()
    
    # Count total documents
    total_documents = db.query(Document).count()
    
    # Count total chunks
    total_chunks = db.query(DocumentChunk).count()
    
    # Count total conversations
    total_conversations = db.query(Conversation).count()
    
    # Count total messages
    total_messages = db.query(Message).count()
    
    # Count active users in last 24 hours
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    active_users = db.query(Message).filter(
        Message.created_at >= twenty_four_hours_ago
    ).distinct(Message.conversation_id).count()
    
    return SystemStats(
        total_users=total_users,
        total_documents=total_documents,
        total_chunks=total_chunks,
        total_conversations=total_conversations,
        total_messages=total_messages,
        active_users_last_24h=active_users
    )


@router.get("/users/stats", response_model=List[UserStats])
async def get_user_stats(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics for all users.
    
    Args:
        skip: Number of users to skip
        limit: Maximum number of users to return
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        List[UserStats]: User statistics
    """
    users = db.query(User).offset(skip).limit(limit).all()
    
    user_stats = []
    for user in users:
        # Count user's documents
        document_count = db.query(Document).filter(
            Document.user_id == user.id
        ).count()
        
        # Count user's conversations
        conversation_count = db.query(Conversation).filter(
            Conversation.user_id == user.id
        ).count()
        
        # Count user's messages
        message_count = db.query(Message).join(Conversation).filter(
            Conversation.user_id == user.id
        ).count()
        
        # Get last activity
        last_message = db.query(Message).join(Conversation).filter(
            Conversation.user_id == user.id
        ).order_by(Message.created_at.desc()).first()
        
        last_activity = last_message.created_at.isoformat() if last_message else None
        
        user_stats.append(UserStats(
            user_id=user.id,
            username=user.username,
            email=user.email,
            document_count=document_count,
            conversation_count=conversation_count,
            message_count=message_count,
            last_activity=last_activity
        ))
    
    return user_stats


@router.get("/documents/stats", response_model=List[DocumentStats])
async def get_document_stats(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics for all documents.
    
    Args:
        skip: Number of documents to skip
        limit: Maximum number of documents to return
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        List[DocumentStats]: Document statistics
    """
    documents = db.query(Document).order_by(
        Document.uploaded_at.desc()
    ).offset(skip).limit(limit).all()
    
    document_stats = []
    for doc in documents:
        # Count chunks
        chunk_count = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc.id
        ).count()
        
        # Get user info
        user = db.query(User).filter(User.id == doc.user_id).first()
        
        document_stats.append(DocumentStats(
            document_id=doc.id,
            filename=doc.filename,
            user_id=doc.user_id,
            username=user.username if user else "Unknown",
            page_count=doc.page_count,
            chunk_count=chunk_count,
            uploaded_at=doc.uploaded_at.isoformat(),
            processed_at=doc.processed_at.isoformat() if doc.processed_at else None
        ))
    
    return document_stats


@router.get("/health")
async def health_check(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Health check endpoint for monitoring.
    
    Args:
        current_user: Current authenticated admin user
        
    Returns:
        dict: Health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "RAG Platform"
    }


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Activate a user account.
    
    Args:
        user_id: User ID to activate
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        dict: Activation status
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    db.commit()
    
    logger.info(f"User {user_id} activated by admin {current_user.id}")
    
    return {"status": "activated", "user_id": user_id}


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Deactivate a user account.
    
    Args:
        user_id: User ID to deactivate
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        dict: Deactivation status
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = False
    db.commit()
    
    logger.info(f"User {user_id} deactivated by admin {current_user.id}")
    
    return {"status": "deactivated", "user_id": user_id}


@router.get("/storage/usage")
async def get_storage_usage(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get storage usage statistics.
    
    Args:
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        dict: Storage usage information
    """
    import os
    
    # Calculate total file size
    total_file_size = db.query(func.sum(Document.file_size)).scalar() or 0
    
    # Get upload directory size
    upload_dir_size = 0
    upload_dir = "./data/uploads"
    if os.path.exists(upload_dir):
        for dirpath, dirnames, filenames in os.walk(upload_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    upload_dir_size += os.path.getsize(filepath)
    
    # Get vector store directory size
    vector_store_size = 0
    vector_store_dir = "./data/vector_stores"
    if os.path.exists(vector_store_dir):
        for dirpath, dirnames, filenames in os.walk(vector_store_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    vector_store_size += os.path.getsize(filepath)
    
    return {
        "total_file_size_bytes": total_file_size,
        "total_file_size_mb": round(total_file_size / (1024 * 1024), 2),
        "upload_dir_size_bytes": upload_dir_size,
        "upload_dir_size_mb": round(upload_dir_size / (1024 * 1024), 2),
        "vector_store_size_bytes": vector_store_size,
        "vector_store_size_mb": round(vector_store_size / (1024 * 1024), 2),
        "total_storage_bytes": total_file_size + upload_dir_size + vector_store_size,
        "total_storage_mb": round((total_file_size + upload_dir_size + vector_store_size) / (1024 * 1024), 2)
    }
