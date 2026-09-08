import os
import io
from typing import Optional

from PyPDF2 import PdfReader
from docx import Document


class DocumentProcessor:
    """Extract text from various document formats."""
    
    @staticmethod
    def extract_text(file_content: bytes, filename: str) -> Optional[str]:
        """Extract text from file content based on extension."""
        file_ext = os.path.splitext(filename)[1].lower()
        
        try:
            if file_ext == ".pdf":
                return DocumentProcessor._extract_pdf(file_content)
            elif file_ext == ".docx":
                return DocumentProcessor._extract_docx(file_content)
            elif file_ext in [".txt", ".md"]:
                return DocumentProcessor._extract_text(file_content)
            else:
                return None
                
        except Exception as e:
            print(f"Failed to extract {filename}: {e}")
            return None
    
    @staticmethod
    def _extract_pdf(content: bytes) -> str:
        """Extract text from PDF."""
        reader = PdfReader(io.BytesIO(content))
        text_parts = []
        
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        
        return "\n".join(text_parts)
    
    @staticmethod
    def _extract_docx(content: bytes) -> str:
        """Extract text from DOCX."""
        doc = Document(io.BytesIO(content))
        text_parts = []
        
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        
        return "\n".join(text_parts)
    
    @staticmethod
    def _extract_text(content: bytes) -> str:
        """Extract text from plain text files."""
        # Try UTF-8 first, fallback to latin-1
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1")
    
    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> list[str]:
        """Split text into overlapping chunks."""
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence or paragraph
            if end < len(text):
                # Look for sentence break
                for i in range(end, max(start + chunk_size // 2, end - 100), -1):
                    if i < len(text) and text[i] in ".!?\n":
                        end = i + 1
                        break
            
            chunks.append(text[start:end].strip())
            start = end - chunk_overlap
        
        return [c for c in chunks if c]


# Global instance
document_processor = DocumentProcessor()
