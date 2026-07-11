"""
Chat Router Module

This module handles chat endpoints for interacting with documents using RAG.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database.connection import get_db
from app.models.user import User
from app.models.document import Document
from app.models.conversation import Conversation
from app.models.chunk import DocumentChunk
from app.utils.auth import get_current_active_user
from app.services.embedding import get_embedding_service
from app.services.vector_store import get_vector_store
from app.services.reranker import get_reranker_service
from app.services.query_expansion import get_query_expansion_service
from app.services.conversation_memory import ConversationMemoryService
from app.core.config import get_settings
from loguru import logger
import os
import json

settings = get_settings()

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


# Pydantic models
class ChatRequest(BaseModel):
    """Chat request model."""
    query: str
    document_id: Optional[int] = None
    conversation_id: Optional[int] = None
    use_reranking: bool = True
    use_query_expansion: bool = True


class ChatResponse(BaseModel):
    """Chat response model."""
    answer: str
    sources: List[dict]
    conversation_id: int


class Citation(BaseModel):
    """Citation model."""
    chunk_id: int
    document_id: int
    document_title: str
    page_number: int
    text: str
    relevance_score: float


class ConversationResponse(BaseModel):
    """Conversation response model."""
    id: int
    title: str
    document_id: Optional[int]
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    """Message response model."""
    id: int
    role: str
    content: str
    citations: Optional[List[dict]]
    created_at: str


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Process a chat query using RAG.
    
    Args:
        request: Chat request with query and context
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ChatResponse: Answer with sources
    """
    # Validate document access if specified
    if request.document_id:
        document = db.query(Document).filter(
            Document.id == request.document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        if not document.is_processed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document is still being processed"
            )
    
    # Get or create conversation
    conversation_memory = ConversationMemoryService(db)
    
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    else:
        conversation = conversation_memory.create_conversation(
            user_id=current_user.id,
            document_id=request.document_id,
            title=request.query[:50] + "..." if len(request.query) > 50 else request.query
        )
    
    # Add user message to conversation
    conversation_memory.add_message(
        conversation_id=conversation.id,
        role="user",
        content=request.query
    )
    
    # Perform semantic search
    try:
        # Get embedding service
        embedding_service = get_embedding_service()
        
        # Expand query if enabled
        queries = [request.query]
        if request.use_query_expansion:
            query_expansion_service = get_query_expansion_service()
            queries = query_expansion_service.expand_query(request.query)
        
        # Search for relevant chunks
        all_results = []
        for expanded_query in queries:
            query_embedding = embedding_service.encode_single(expanded_query)
            
            # Search in all user's documents or specific document
            if request.document_id:
                documents_to_search = [request.document_id]
            else:
                user_documents = db.query(Document).filter(
                    Document.user_id == current_user.id,
                    Document.is_processed == 1
                ).all()
                documents_to_search = [doc.id for doc in user_documents]
            
            for doc_id in documents_to_search:
                try:
                    # Load vector store
                    vector_store_path = os.path.join(
                        settings.VECTOR_STORE_PATH,
                        f"document_{doc_id}.index"
                    )
                    
                    if not os.path.exists(vector_store_path):
                        continue
                    
                    dimension = embedding_service.get_embedding_dimension()
                    vector_store = get_vector_store(doc_id, dimension)
                    vector_store.load_index(vector_store_path)
                    
                    # Search
                    distances, indices = vector_store.search(query_embedding, k=5)
                    
                    # Get chunk information
                    for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                        chunk_id = vector_store.get_document_id(int(idx))
                        if chunk_id:
                            chunk = db.query(DocumentChunk).filter(
                                DocumentChunk.id == chunk_id
                            ).first()
                            
                            if chunk:
                                all_results.append({
                                    "chunk": chunk,
                                    "score": float(distance),
                                    "document_id": doc_id
                                })
                
                except Exception as e:
                    logger.error(f"Error searching document {doc_id}: {e}")
                    continue
        
        # Re-rank results if enabled
        if request.use_reranking and all_results:
            reranker = get_reranker_service()
            chunk_texts = [r["chunk"].chunk_text for r in all_results]
            ranked_results = reranker.rerank(request.query, chunk_texts, top_k=5)
            
            # Reorder results
            reranked = []
            for rank_idx, score in ranked_results:
                reranked.append(all_results[rank_idx])
            all_results = reranked
        
        # Generate answer (simplified - in production, use LLM)
        answer = generate_answer(request.query, all_results[:3])
        
        # Create citations
        citations = []
        for result in all_results[:3]:
            chunk = result["chunk"]
            document = db.query(Document).filter(Document.id == chunk.document_id).first()
            
            citations.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "document_title": document.title if document else "Unknown",
                "page_number": chunk.page_number,
                "text": chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text,
                "relevance_score": result["score"]
            })
        
        # Add assistant message to conversation
        conversation_memory.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            citations=citations
        )
        
        return ChatResponse(
            answer=answer,
            sources=citations,
            conversation_id=conversation.id
        )
    
    except Exception as e:
        logger.error(f"Error processing chat query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process query"
        )


def generate_answer(query: str, relevant_chunks: List[dict]) -> str:
    """
    Generate an answer from relevant chunks.
    
    In production, this should use an LLM like GPT-4, Claude, etc.
    For now, we'll provide a simple response based on the chunks.
    
    Args:
        query: User query
        relevant_chunks: List of relevant chunks with metadata
        
    Returns:
        str: Generated answer
    """
    if not relevant_chunks:
        return "I couldn't find relevant information in the documents to answer your question."
    
    # Simple answer generation (replace with LLM in production)
    answer_parts = ["Based on the documents, here's what I found:\n"]
    
    for i, result in enumerate(relevant_chunks, 1):
        chunk = result["chunk"]
        answer_parts.append(f"\n{i}. From page {chunk.page_number}:")
        answer_parts.append(chunk.chunk_text[:300] + "..." if len(chunk.chunk_text) > 300 else chunk.chunk_text)
    
    answer_parts.append("\n\nNote: This is a simple response. In production, an LLM would generate a more comprehensive answer.")
    
    return "".join(answer_parts)


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List user's conversations.
    
    Args:
        skip: Number of conversations to skip
        limit: Maximum number of conversations to return
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[ConversationResponse]: List of conversations
    """
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()
    
    return [
        ConversationResponse(
            id=conv.id,
            title=conv.title,
            document_id=conv.document_id,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat() if conv.updated_at else conv.created_at.isoformat()
        )
        for conv in conversations
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get messages from a conversation.
    
    Args:
        conversation_id: Conversation ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[MessageResponse]: List of messages
    """
    # Verify conversation ownership
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    conversation_memory = ConversationMemoryService(db)
    messages = conversation_memory.get_conversation_history(conversation_id)
    
    return [
        MessageResponse(
            id=msg["id"],
            role=msg["role"],
            content=msg["content"],
            citations=msg["citations"],
            created_at=msg["created_at"]
        )
        for msg in messages
    ]


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a conversation.
    
    Args:
        conversation_id: Conversation ID
        current_user: Current authenticated user
        db: Database session
        
    Raises:
        HTTPException: If conversation not found or access denied
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    conversation_memory = ConversationMemoryService(db)
    conversation_memory.delete_conversation(conversation_id)


@router.get("/conversations/{conversation_id}/export")
async def export_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Export conversation as JSON.
    
    Args:
        conversation_id: Conversation ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        dict: Conversation data
    """
    # Verify conversation ownership
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    conversation_memory = ConversationMemoryService(db)
    messages = conversation_memory.get_conversation_history(conversation_id)
    
    return {
        "conversation_id": conversation_id,
        "title": conversation.title,
        "document_id": conversation.document_id,
        "created_at": conversation.created_at.isoformat(),
        "messages": messages
    }
