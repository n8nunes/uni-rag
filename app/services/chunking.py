import io
import pdfplumber
from typing import List, Dict, Any
from app.models.schemas import DocumentMetadata

class DocumentProcessor:
    @staticmethod
    def chunk_text(
        raw_text: str,
        metadata: DocumentMetadata,
        chunk_size: int = 500, 
        chunk_overlap: int = 50
    ) -> List[Dict[str, Any]]:
        chunks = []
        words = raw_text.split()

        if chunk_size <= chunk_overlap:
            raise ValueError("chunk_size must be greater than chunk_overlap.")

        for i in range(0, len(words), chunk_size - chunk_overlap):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)

            if chunk_text.strip():
                chunks.append(
                    {
                        "text": chunk_text,
                        "metadata": metadata.model_dump(mode="json"),
                    }
                )

        return chunks

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
        raw_text = ""

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    raw_text += text + "\n"

        return DocumentProcessor.chunk_text(raw_text, metadata, chunk_size, chunk_overlap)

    @staticmethod
    async def extract_and_chunk_markdown(
        file_bytes: bytes,
        metadata: DocumentMetadata,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Parses Markdown/plain text bytes, chunks text, and applies security metadata.
        """
        raw_text = file_bytes.decode("utf-8-sig", errors="replace")
        return DocumentProcessor.chunk_text(raw_text, metadata, chunk_size, chunk_overlap)

    @staticmethod
    async def extract_and_chunk_file(
        filename: str,
        file_bytes: bytes,
        metadata: DocumentMetadata,
    ) -> List[Dict[str, Any]]:
        lowered = filename.lower()
        if lowered.endswith(".pdf"):
            return await DocumentProcessor.extract_and_chunk_pdf(file_bytes, metadata)
        if lowered.endswith((".md", ".markdown")):
            return await DocumentProcessor.extract_and_chunk_markdown(file_bytes, metadata)
        raise ValueError("Unsupported file type.")
