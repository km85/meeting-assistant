import os
import time
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.security import log_audit
from app.knowledge_base import knowledge_base
from app.document_processor import document_processor

settings = get_settings()
router = APIRouter(prefix="/projects", tags=["projects"])

# In-memory project storage (replace with DB in production)
projects: dict[str, dict] = {}


@router.post("/create")
async def create_project(name: str = Form(...), description: Optional[str] = Form(None)):
    """Create a new project."""
    project_id = f"project_{int(time.time())}_{name[:20]}"
    
    projects[project_id] = {
        "id": project_id,
        "name": name,
        "description": description,
        "created_at": time.time(),
        "documents": [],
        "status": "active",
    }
    
    log_audit("project_created", details={"project_id": project_id, "name": name})
    
    return {
        "project_id": project_id,
        "name": name,
        "status": "created",
    }


@router.get("/list")
async def list_projects():
    """List all projects."""
    return {
        "projects": [
            {
                "id": p["id"],
                "name": p["name"],
                "description": p["description"],
                "document_count": len(p["documents"]),
                "status": p["status"],
            }
            for p in projects.values()
        ]
    }


@router.post("/{project_id}/upload")
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
):
    """Upload document to project and index in knowledge base."""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate file type
    allowed_extensions = {".pdf", ".docx", ".txt", ".md"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Read file content
    content = await file.read()
    
    # Extract text
    text = document_processor.extract_text(content, file.filename)
    if not text:
        raise HTTPException(status_code=400, detail="Failed to extract text from document")
    
    # Chunk text
    chunks = document_processor.chunk_text(
        text,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    
    # Index in knowledge base
    indexed = knowledge_base.add_documents(
        project_id=project_id,
        chunks=chunks,
        metadata=[{
            "filename": file.filename,
            "chunk_index": i,
            "total_chunks": len(chunks),
        } for i in range(len(chunks))],
    )
    
    doc_id = f"doc_{int(time.time())}_{file.filename[:30]}"
    projects[project_id]["documents"].append({
        "id": doc_id,
        "filename": file.filename,
        "size": len(content),
        "status": "indexed" if indexed else "uploaded",
        "chunks": len(chunks),
        "uploaded_at": time.time(),
    })
    
    log_audit("document_uploaded", details={
        "project_id": project_id,
        "document_id": doc_id,
        "filename": file.filename,
        "chunks": len(chunks),
        "indexed": indexed,
    })
    
    return {
        "document_id": doc_id,
        "filename": file.filename,
        "status": "indexed" if indexed else "uploaded",
        "chunks": len(chunks),
        "message": "Document uploaded and indexed in knowledge base." if indexed else "Document uploaded but indexing failed.",
    }


@router.get("/{project_id}/status")
async def project_status(project_id: str):
    """Get project status."""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = projects[project_id]
    
    return {
        "project_id": project_id,
        "name": project["name"],
        "status": project["status"],
        "documents": [
            {
                "id": d["id"],
                "filename": d["filename"],
                "status": d["status"],
            }
            for d in project["documents"]
        ],
        "document_count": len(project["documents"]),
    }


@router.get("/{project_id}/search")
async def search_project(
    project_id: str,
    query: str,
    limit: int = 5,
):
    """Search project knowledge base."""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    results = knowledge_base.search(
        project_id=project_id,
        query=query,
        limit=limit,
    )
    
    return {
        "project_id": project_id,
        "query": query,
        "results_count": len(results),
        "results": results,
    }


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete project and its knowledge base."""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Delete knowledge base
    knowledge_base.delete_project_collection(project_id)
    
    del projects[project_id]
    log_audit("project_deleted", details={"project_id": project_id})
    
    return {"status": "deleted", "project_id": project_id}
