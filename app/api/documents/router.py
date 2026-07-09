from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from typing import List
from app.models.schemas import ClassificationEnum, UserSession, DocumentMetadata
from app.services.chunking import DocumentProcessor
from app.services.vector_db import vector_db
from app.core.logger import audit_logger
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/documents", tags=["Document Ingestion"])

SUPPORTED_EXTENSIONS = (".pdf", ".md", ".markdown")

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    files: List[UploadFile] = File(...),
    classification: ClassificationEnum = Form(...),
    current_user: UserSession = Depends(get_current_user)
):
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one document must be uploaded.",
        )

    if current_user.role != "admin" and classification != ClassificationEnum.GENERAL:
        audit_logger.warning(
            "Privilege escalation attempt blocked.",
            extra={"extra_context": {"user": current_user.user_id, "attempted_target": classification}},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authorization Failure: Only workplace admins can upload restricted or sensitive documents.",
        )

    processed_results = []
    all_chunks = []

    for file in files:
        filename = file.filename or ""
        if not filename.lower().endswith(SUPPORTED_EXTENSIONS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type for {filename or 'uploaded file'}. Supported types: PDF, MD, Markdown.",
            )

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{filename} is empty.",
            )

        doc_metadata = DocumentMetadata(
            source_file=filename,
            classification=classification,
            uploaded_by=current_user.user_id,
        )

        processed_chunks = await DocumentProcessor.extract_and_chunk_file(filename, file_bytes, doc_metadata)
        if not processed_chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No extractable text found in {filename}.",
            )

        all_chunks.extend(processed_chunks)
        processed_results.append(
            {
                "file_name": filename,
                "chunks_extracted": len(processed_chunks),
            }
        )

        audit_logger.info(
            "Document successfully processed and tokenized.",
            extra={
                "extra_context": {
                    "event": "DOCUMENT_INGESTION_SUCCESS",
                    "filename": filename,
                    "chunks_generated": len(processed_chunks),
                    "classification": classification,
                    "operator": current_user.user_id,
                }
            },
        )

    await vector_db.upsert_chunks(all_chunks)

    return {
        "message": "Processing executed successfully",
        "files_processed": processed_results,
        "file_count": len(processed_results),
        "chunks_extracted": len(all_chunks),
        "security_policy_applied": classification,
    }
