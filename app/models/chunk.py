"""
Document Chunk Model Module

This module defines the DocumentChunk model for storing text chunks from PDFs.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class DocumentChunk(Base):
    """
    Document chunk model for storing text segments from PDFs.
    
    Attributes:
        id: Primary key
        document_id: Foreign key to document
        chunk_text: Text content of the chunk
        page_number: Page number in the original document
        chunk_index: Index of the chunk in the document
        embedding_vector: Vector embedding (stored as text/binary)
        metadata: Additional metadata as JSON
        created_at: Creation timestamp
    """
    
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    page_number = Column(Integer, default=0)
    chunk_index = Column(Integer, default=0)
    embedding_vector = Column(Text)  # Store as serialized text
    metadata = Column(Text)  # Store as JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, page={self.page_number})>"
