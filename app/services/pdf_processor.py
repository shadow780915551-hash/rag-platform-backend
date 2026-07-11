"""
PDF Processing Service Module

This module handles PDF text extraction, chunking with overlap optimization,
and preparation for embedding.
"""

import PyPDF2
import pdfplumber
from typing import List, Dict, Tuple
import re
from app.core.config import get_settings
from loguru import logger

settings = get_settings()


class PDFProcessor:
    """
    Service for processing PDF documents.
    
    This service provides methods to extract text from PDFs,
    chunk it with overlap optimization, and prepare it for embedding.
    """
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        """
        Initialize the PDF processor.
        
        Args:
            chunk_size: Size of text chunks in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        logger.info(f"PDF processor initialized with chunk_size={self.chunk_size}, overlap={self.chunk_overlap}")
    
    def extract_text(self, pdf_path: str) -> List[Dict]:
        """
        Extract text from PDF file page by page.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List[Dict]: List of pages with text and metadata
        """
        pages = []
        
        try:
            # Try pdfplumber first (better text extraction)
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        pages.append({
                            "page_number": page_num + 1,
                            "text": text.strip(),
                            "char_count": len(text)
                        })
            
            logger.info(f"Extracted text from {len(pages)} pages using pdfplumber")
            
        except Exception as e:
            logger.warning(f"pdfplumber failed, falling back to PyPDF2: {e}")
            
            # Fallback to PyPDF2
            try:
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page_num, page in enumerate(pdf_reader.pages):
                        text = page.extract_text()
                        if text:
                            pages.append({
                                "page_number": page_num + 1,
                                "text": text.strip(),
                                "char_count": len(text)
                            })
                
                logger.info(f"Extracted text from {len(pages)} pages using PyPDF2")
            
            except Exception as e2:
                logger.error(f"Failed to extract text with both methods: {e2}")
                raise
        
        return pages
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.
        
        Args:
            text: Raw text to clean
            
        Returns:
            str: Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\?\!\-\:\;\(\)]', '', text)
        
        # Remove page numbers and headers/footers (simple heuristic)
        text = re.sub(r'\n\d+\n', ' ', text)
        
        return text.strip()
    
    def chunk_text(
        self,
        text: str,
        page_number: int = 0
    ) -> List[Dict]:
        """
        Chunk text with overlap optimization.
        
        Args:
            text: Text to chunk
            page_number: Page number for metadata
            
        Returns:
            List[Dict]: List of text chunks with metadata
        """
        chunks = []
        text_length = len(text)
        
        # If text is shorter than chunk size, return as single chunk
        if text_length <= self.chunk_size:
            chunks.append({
                "text": text,
                "page_number": page_number,
                "chunk_index": 0,
                "char_count": len(text)
            })
            return chunks
        
        # Chunk with overlap
        start = 0
        chunk_index = 0
        
        while start < text_length:
            # Calculate end position
            end = start + self.chunk_size
            
            # If this is the last chunk, take remaining text
            if end >= text_length:
                chunk_text = text[start:]
                chunks.append({
                    "text": chunk_text,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "char_count": len(chunk_text)
                })
                break
            
            # Try to break at sentence boundary
            chunk_text = text[start:end]
            
            # Look for sentence endings in the last 100 characters
            last_100_chars = chunk_text[-100:]
            sentence_endings = [m.end() for m in re.finditer(r'[.!?]\s+', last_100_chars)]
            
            if sentence_endings:
                # Break at the last sentence ending
                break_pos = len(chunk_text) - 100 + sentence_endings[-1]
                chunk_text = text[start:break_pos]
                start = break_pos - self.chunk_overlap
            else:
                # No sentence ending found, break at word boundary
                last_space = chunk_text.rfind(' ')
                if last_space > 0:
                    chunk_text = text[start:start + last_space]
                    start = start + last_space - self.chunk_overlap
                else:
                    # No word boundary, force break
                    start = end - self.chunk_overlap
            
            # Ensure start doesn't go negative
            start = max(0, start)
            
            chunks.append({
                "text": chunk_text.strip(),
                "page_number": page_number,
                "chunk_index": chunk_index,
                "char_count": len(chunk_text)
            })
            
            chunk_index += 1
        
        return chunks
    
    def process_pdf(self, pdf_path: str) -> List[Dict]:
        """
        Process PDF file: extract text, clean, and chunk.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List[Dict]: List of processed chunks with metadata
        """
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Extract text from PDF
        pages = self.extract_text(pdf_path)
        
        if not pages:
            logger.warning(f"No text extracted from PDF: {pdf_path}")
            return []
        
        # Process each page
        all_chunks = []
        for page in pages:
            # Clean text
            cleaned_text = self.clean_text(page["text"])
            
            if not cleaned_text:
                continue
            
            # Chunk text
            chunks = self.chunk_text(cleaned_text, page["page_number"])
            all_chunks.extend(chunks)
        
        logger.info(f"Generated {len(all_chunks)} chunks from {len(pages)} pages")
        
        return all_chunks
    
    def get_document_metadata(self, pdf_path: str) -> Dict:
        """
        Get metadata from PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dict: Document metadata
        """
        metadata = {
            "page_count": 0,
            "title": "",
            "author": "",
            "creator": ""
        }
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                metadata["page_count"] = len(pdf_reader.pages)
                
                # Extract PDF info
                pdf_info = pdf_reader.metadata
                if pdf_info:
                    metadata["title"] = pdf_info.get("/Title", "")
                    metadata["author"] = pdf_info.get("/Author", "")
                    metadata["creator"] = pdf_info.get("/Creator", "")
        
        except Exception as e:
            logger.error(f"Failed to extract PDF metadata: {e}")
        
        return metadata


# Global PDF processor instance
_pdf_processor = None


def get_pdf_processor() -> PDFProcessor:
    """
    Get or create the global PDF processor instance.
    
    Returns:
        PDFProcessor: Global PDF processor instance
    """
    global _pdf_processor
    if _pdf_processor is None:
        _pdf_processor = PDFProcessor()
    return _pdf_processor
