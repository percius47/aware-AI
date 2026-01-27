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
    
    async def process_pdf(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Process PDF file"""
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        texts = []
        
        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if text.strip():
                texts.append({
                    "text": text,
                    "page": page_num + 1,
                    "source": filename
                })
        
        # Add to RAG
        document_ids = await self.rag_service.add_documents(
            texts=[item["text"] for item in texts],
            metadatas=[{
                "type": "pdf",
                "filename": filename,
                "page": item["page"]
            } for item in texts]
        )
        
        return {
            "chunks": len(texts),
            "document_ids": document_ids,
            "type": "pdf"
        }
    
    async def process_docx(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Process DOCX file"""
        doc = Document(io.BytesIO(file_content))
        texts = []
        
        for para in doc.paragraphs:
            if para.text.strip():
                texts.append({
                    "text": para.text,
                    "source": filename
                })
        
        # Add to RAG
        document_ids = await self.rag_service.add_documents(
            texts=[item["text"] for item in texts],
            metadatas=[{
                "type": "docx",
                "filename": filename
            } for item in texts]
        )
        
        return {
            "chunks": len(texts),
            "document_ids": document_ids,
            "type": "docx"
        }
    
    async def process_text(self, content: str, filename: str) -> Dict[str, Any]:
        """Process plain text"""
        # Split into chunks (simple approach)
        chunk_size = 1000
        chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
        
        document_ids = await self.rag_service.add_documents(
            texts=chunks,
            metadatas=[{
                "type": "text",
                "filename": filename
            } for _ in chunks]
        )
        
        return {
            "chunks": len(chunks),
            "document_ids": document_ids,
            "type": "text"
        }
    
    async def process_file(self, file_content: bytes, filename: str, content_type: str) -> Dict[str, Any]:
        """Process any supported file type"""
        if content_type == "application/pdf":
            return await self.process_pdf(file_content, filename)
        elif content_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
            return await self.process_docx(file_content, filename)
        elif content_type.startswith("text/"):
            return await self.process_text(file_content.decode("utf-8"), filename)
        else:
            raise ValueError(f"Unsupported file type: {content_type}")
