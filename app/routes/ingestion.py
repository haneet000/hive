from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import IngestionRejectSchema
from app.crud import get_ingestion_rejects

router = APIRouter(prefix="/ingestion", tags=["Ingestion Audit"])

@router.get(
    "/rejects",
    response_model=List[IngestionRejectSchema],
    summary="Get Ingestion Rejects / Audit Log",
    description="Returns data quality validation rejects and warnings logged during ingestion (duplicate order IDs, orphaned customer IDs, unparseable dates)."
)
def list_rejects(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    return get_ingestion_rejects(db=db, page=page, limit=limit)
