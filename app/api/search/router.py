from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import ClassificationEnum, SearchRequest, SearchResponse, SourceReference, UserSession
from app.services.vector_db import vector_db
from app.services.ollama_client import ollama_client
from app.core.logger import audit_logger
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/search", tags=["Secure RAG Engine"])

@router.post("/query", response_model=SearchResponse)
async def secure_rag_query(
    request: SearchRequest,
    current_user: UserSession = Depends(get_current_user)
):
    query = request.query
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be blank.")

    authorized_chunks = await vector_db.secure_similarity_search(
        query=query,
        user_clearance=current_user.clearance_level,
        top_k=request.top_k,
        user_role=current_user.role,
    )

    if not authorized_chunks:
        context_payload = "No authorized context found for this user clearance profile."
    else:
        context_payload = "\n".join([chunk["text"] for chunk in authorized_chunks])

    history_payload = [message.model_dump() for message in request.history]
    allow_web_research = bool(authorized_chunks) and all(
        str(chunk.get("metadata", {}).get("classification", "")).lower() == ClassificationEnum.GENERAL.value.lower()
        for chunk in authorized_chunks
    )
    ai_response = await ollama_client.generate_response(
        prompt=query,
        context=context_payload,
        conversation_history=history_payload,
        allow_web_research=allow_web_research,
    )

    audit_logger.info(
        "RAG inquiry completed.",
        extra={
            "extra_context": {
                "event": "DATA_RETRIEVAL_QUERY",
                "operator": current_user.user_id,
                "clearance_level_used": current_user.clearance_level,
                "sources_accessed": [c["metadata"]["source_file"] for c in authorized_chunks],
            }
        },
    )

    return {
        "query": query,
        "response": ai_response,
        "access_clearance_applied": current_user.clearance_level,
        "sources_consulted": [
            SourceReference(
                source_file=c["metadata"]["source_file"],
                classification=c["metadata"]["classification"],
                score=c.get("score"),
            )
            for c in authorized_chunks
        ],
    }
