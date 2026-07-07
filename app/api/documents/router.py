from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from app.models.schemas import ClassificationEnum, UserSession, DocumentMetadata
from app.services.chunking import DocumentProcessor
from app.core.logger import audit_logger
import json

router = APIRouter(prefix="/documents", tags=["Document Ingestion"])

# Security Mock Dependency representing verified JWT extraction
async def get_current_user() -> UserSession:
    return UserSession(
        user_id="user_dev_01",
        username="norman_student",
        role="student",
        clearance_level=ClassificationEnum.STUDENT_ONLY
    )

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    classification: ClassificationEnum = Form(...),
    current_user: UserSession = Depends(get_current_user)
):
    # Verify File Type Extensions
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Unsupported File Type. System mandates PDF processing."
        )

    # Enforce Governance Check: Users cannot tag documents above their clearance level
    if (current_user.clearance_level == ClassificationEnum.STUDENT_ONLY and 
        classification == ClassificationEnum.RESTRICTED):
        
        audit_logger.warning(
            f"Privilege escalation attempt blocked.",
            extra={"extra_context": {"user": current_user.user_id, "attempted_target": classification}}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authorization Failure: Target classification exceeds user clearance parameters."
        )

    # Read binary file contents
    file_bytes = await file.read()
    
    # Construct Immutable Audit Records
    doc_metadata = DocumentMetadata(
        source_file=file.filename,
        classification=classification,
        uploaded_by=current_user.user_id
    )
    
    # Execute Asynchronous Parsing Core Engine
    processed_chunks = await DocumentProcessor.extract_and_chunk_pdf(file_bytes, doc_metadata)
    
    # SOC 2 Audit Trail Tracking Emitted to Stdout/Collector
    audit_logger.info(
        f"Document successfully processed and tokenized.",
        extra={
            "extra_context": {
                "event": "DOCUMENT_INGESTION_SUCCESS",
                "filename": file.filename,
                "chunks_generated": len(processed_chunks),
                "classification": classification,
                "operator": current_user.user_id
            }
        }
    )
    
    return {
        "message": "Processing executed successfully",
        "file_name": file.filename,
        "chunks_extracted": len(processed_chunks),
        "security_policy_applied": classification
    }