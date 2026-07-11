"""
Document Model Module

This module defines the Document model for storing PDF metadata and information.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Document(Base):
    """
    Document model for storing PDF metadata.
    
    Attributes:
        id: Primary key
        filename: Original filename
        file_path: Storage path
        file_size: File size in bytes
        page_count: Number of pages
        title: Document title
        description: Document description
        user_id: Foreign key to user
        uploaded_at: Upload timestamp
        processed_at: Processing completion timestamp
        is_processed: Processing status
    """
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    page_count = Column(Integer, default=0)
    title = Column(String)
    description = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    is_processed = Column(Integer, default=0)
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, user_id={self.user_id})>"
