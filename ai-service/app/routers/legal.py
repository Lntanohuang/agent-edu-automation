"""
法律法规上传路由
"""
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
import tempfile
import os
from typing import Dict, Any

from app.core.logging import get_logger
from app.services.rag_docu import RagService

router = APIRouter()
logger = get_logger(__name__)
rag_service = RagService()


class UploadLegalResponse(BaseModel):
    success: bool = True
    stats: Dict[str, Any] = {}


@router.post("/upload", response_model=UploadLegalResponse)
async def upload_legal_file(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        stats = rag_service.docu_rag(tmp_path)
        return UploadLegalResponse(success=True, stats=stats)
    finally:
        os.remove(tmp_path)
