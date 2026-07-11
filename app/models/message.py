"""
Message Model Module

This module defines the Message model for storing conversation messages.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Message(Base):
    """
    Message model for storing conversation messages.
    
    Attributes:
        id: Primary key
        conversation_id: Foreign key to conversation
        role: Message role (user, assistant, system)
        content: Message content
        citations: Source citations as JSON
        created_at: Creation timestamp
    """
    
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    citations = Column(Text)  # Store as JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, role={self.role})>"
