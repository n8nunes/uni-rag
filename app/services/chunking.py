import io
import pdfplumber
from typing import List, Dict, Any
from app.models.schemas import DocumentMetadata

class DocumentProcessor:
    @staticmethod
    async def extract_and_chunk_pdf(
        file_bytes: bytes, 
        metadata: DocumentMetadata, 
        chunk_size: int = 500, 
        chunk_overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Parses a PDF byte stream, chunks text, and applies structural security metadata.
        """
        chunks = []
        raw_text = ""
        
        # Read the byte stream asynchronously using pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    raw_text += text + "\n"
                    
        # Token-based parsing simulation using sliding window words
        words = raw_text.split()
        for i in range(0, len(words), chunk_size - chunk_overlap):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)
            
            if chunk_text.strip():
                chunks.append({
                    "text": chunk_text,
                    # Crucial: Deep copy metadata attributes to each vector candidate
                    "metadata": metadata.dict()
                })
                
        return chunks