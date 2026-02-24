import PyPDF2
from docx import Document
from PIL import Image
import io
import os
from typing import List, Dict, Any
from app.services.rag_service import RAGService

class DocumentProcessor:
    def __init__(self):
        self.rag_service = RAGService()
    
    def _sanitize_text(self, text: str) -> str:
        """Remove null bytes and other problematic characters that PostgreSQL can't handle."""
        if not text:
            return ""
        # Remove null bytes (\x00) that PostgreSQL TEXT columns reject
        text = text.replace('\x00', '')
        # Remove other potentially problematic control characters (except newlines/tabs)
        text = ''.join(char for char in text if char == '\n' or char == '\t' or char == '\r' or not (0 <= ord(char) < 32))
        return text
    
    async def process_pdf(self, file_content: bytes, filename: str, user_id: str) -> Dict[str, Any]:
        """Process PDF file with overlapping chunks for better retrieval"""
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        
        full_text = ""
        page_breaks = []
        
        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if text:
                text = self._sanitize_text(text)
                if text.strip():
                    page_breaks.append((len(full_text), page_num + 1))
                    full_text += text + "\n\n"
        
        chunk_size = 1000
        overlap = 200
        chunks = []
        
        for i in range(0, len(full_text), chunk_size - overlap):
            chunk = full_text[i:i + chunk_size]
            if chunk.strip():
                page = 1
                for start_pos, page_num in page_breaks:
                    if i >= start_pos:
                        page = page_num
                chunks.append({
                    "text": chunk,
                    "page": page,
                    "chunk_index": len(chunks)
                })
        
        if not chunks and full_text.strip():
            chunks = [{"text": full_text, "page": 1, "chunk_index": 0}]
        
        document_ids = await self.rag_service.add_documents(
            texts=[item["text"] for item in chunks],
            metadatas=[{
                "type": "pdf",
                "filename": filename,
                "page": item["page"],
                "chunk_index": item["chunk_index"]
            } for item in chunks],
            user_id=user_id
        )
        
        return {
            "chunks": len(chunks),
            "document_ids": document_ids,
            "type": "pdf"
        }
    
    async def process_docx(self, file_content: bytes, filename: str, user_id: str) -> Dict[str, Any]:
        """Process DOCX file with overlapping chunks for better retrieval"""
        doc = Document(io.BytesIO(file_content))
        
        full_text = "\n\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        full_text = self._sanitize_text(full_text)
        
        chunk_size = 1000
        overlap = 200
        chunks = []
        
        for i in range(0, len(full_text), chunk_size - overlap):
            chunk = full_text[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk)
        
        if not chunks and full_text.strip():
            chunks = [full_text]
        
        document_ids = await self.rag_service.add_documents(
            texts=chunks,
            metadatas=[{
                "type": "docx",
                "filename": filename,
                "chunk_index": idx
            } for idx in range(len(chunks))],
            user_id=user_id
        )
        
        return {
            "chunks": len(chunks),
            "document_ids": document_ids,
            "type": "docx"
        }
    
    async def process_text(self, content: str, filename: str, user_id: str) -> Dict[str, Any]:
        """Process plain text with overlapping chunks for better retrieval"""
        content = self._sanitize_text(content)
        chunk_size = 1000
        overlap = 200
        chunks = []
        
        for i in range(0, len(content), chunk_size - overlap):
            chunk = content[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk)
        
        if not chunks:
            chunks = [content] if content.strip() else []
        
        document_ids = await self.rag_service.add_documents(
            texts=chunks,
            metadatas=[{
                "type": "text",
                "filename": filename,
                "chunk_index": idx
            } for idx in range(len(chunks))],
            user_id=user_id
        )
        
        return {
            "chunks": len(chunks),
            "document_ids": document_ids,
            "type": "text"
        }
    
    async def process_file(self, file_content: bytes, filename: str, content_type: str, user_id: str) -> Dict[str, Any]:
        """Process any supported file type"""
        if content_type == "application/pdf":
            return await self.process_pdf(file_content, filename, user_id)
        elif content_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
            return await self.process_docx(file_content, filename, user_id)
        elif content_type.startswith("text/"):
            return await self.process_text(file_content.decode("utf-8"), filename, user_id)
        else:
            raise ValueError(f"Unsupported file type: {content_type}")
