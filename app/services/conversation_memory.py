"""
Conversation Memory Service Module

This module handles conversation memory management for multi-turn dialogues.
"""

from typing import List, Dict, Optional
from datetime import datetime
from app.models.conversation import Conversation
from app.models.message import Message
from sqlalchemy.orm import Session
from loguru import logger


class ConversationMemoryService:
    """
    Service for managing conversation memory.
    
    This service provides methods to store, retrieve, and manage
    conversation history for context-aware responses.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the conversation memory service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_conversation(
        self,
        user_id: int,
        document_id: Optional[int] = None,
        title: str = "New Conversation"
    ) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            user_id: User ID
            document_id: Optional document ID
            title: Conversation title
            
        Returns:
            Conversation: Created conversation
        """
        try:
            conversation = Conversation(
                user_id=user_id,
                document_id=document_id,
                title=title
            )
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)
            
            logger.info(f"Created conversation {conversation.id} for user {user_id}")
            return conversation
        
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            self.db.rollback()
            raise
    
    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        citations: Optional[List[Dict]] = None
    ) -> Message:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: Conversation ID
            role: Message role (user, assistant, system)
            content: Message content
            citations: Optional list of citation dictionaries
            
        Returns:
            Message: Created message
        """
        try:
            import json
            
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                citations=json.dumps(citations) if citations else None
            )
            self.db.add(message)
            
            # Update conversation timestamp
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            if conversation:
                conversation.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(message)
            
            logger.info(f"Added message {message.id} to conversation {conversation_id}")
            return message
        
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            self.db.rollback()
            raise
    
    def get_conversation_history(
        self,
        conversation_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get conversation history.
        
        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List[Dict]: List of message dictionaries
        """
        try:
            import json
            
            messages = self.db.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at).limit(limit).all()
            
            history = []
            for message in messages:
                message_dict = {
                    "id": message.id,
                    "role": message.role,
                    "content": message.content,
                    "citations": json.loads(message.citations) if message.citations else None,
                    "created_at": message.created_at.isoformat()
                }
                history.append(message_dict)
            
            return history
        
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            raise
    
    def get_conversation_context(
        self,
        conversation_id: int,
        max_tokens: int = 2000
    ) -> str:
        """
        Get conversation context as a formatted string.
        
        Args:
            conversation_id: Conversation ID
            max_tokens: Maximum tokens for context
            
        Returns:
            str: Formatted conversation context
        """
        try:
            history = self.get_conversation_history(conversation_id)
            
            context_parts = []
            total_length = 0
            
            # Add messages from most recent to oldest
            for message in reversed(history):
                message_text = f"{message['role'].capitalize()}: {message['content']}\n"
                
                if total_length + len(message_text) > max_tokens:
                    break
                
                context_parts.insert(0, message_text)
                total_length += len(message_text)
            
            return "".join(context_parts)
        
        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}")
            return ""
    
    def get_user_conversations(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[Conversation]:
        """
        Get all conversations for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of conversations
            
        Returns:
            List[Conversation]: List of conversations
        """
        try:
            conversations = self.db.query(Conversation).filter(
                Conversation.user_id == user_id
            ).order_by(Conversation.updated_at.desc()).limit(limit).all()
            
            return conversations
        
        except Exception as e:
            logger.error(f"Failed to get user conversations: {e}")
            raise
    
    def delete_conversation(self, conversation_id: int) -> bool:
        """
        Delete a conversation and all its messages.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if conversation:
                self.db.delete(conversation)
                self.db.commit()
                logger.info(f"Deleted conversation {conversation_id}")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")
            self.db.rollback()
            raise
    
    def update_conversation_title(
        self,
        conversation_id: int,
        title: str
    ) -> Conversation:
        """
        Update conversation title.
        
        Args:
            conversation_id: Conversation ID
            title: New title
            
        Returns:
            Conversation: Updated conversation
        """
        try:
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if conversation:
                conversation.title = title
                self.db.commit()
                self.db.refresh(conversation)
                logger.info(f"Updated title for conversation {conversation_id}")
            
            return conversation
        
        except Exception as e:
            logger.error(f"Failed to update conversation title: {e}")
            self.db.rollback()
            raise
