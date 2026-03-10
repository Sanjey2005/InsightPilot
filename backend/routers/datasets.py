import asyncio
import functools
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from core.auth import get_current_user
from core.database import get_db
from models.dataset import Dataset
from models.user import User
from schemas.dataset import DatasetListItem, DatasetUploadResponse, SchemaPreview
from services.ingestion import ingest_csv

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"text/csv", "application/csv", "application/octet-stream"}


@router.post(
    "/upload",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a CSV and receive an immediate schema preview.",
)
async def upload_dataset(
    file: UploadFile = File(..., description="CSV file (max 50 MB)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetUploadResponse:
    # ── Validate file extension ───────────────────────────────────────────
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only .csv files are accepted. PDF, XLSX, and other formats are not supported.",
        )

    contents = await file.read()

    # ── Ingest (parse → store → profile) ─────────────────────────────────
    # Run in a thread pool executor so the synchronous pandas/SQLite work
    # (read_csv + df.to_sql) doesn't block the asyncio event loop and freeze
    # all other incoming requests.
    try:
        loop = asyncio.get_event_loop()
        _, table_name, schema_preview = await loop.run_in_executor(
            None,
            functools.partial(ingest_csv, contents, file.filename, current_user.id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error while processing CSV: {exc}",
        )

    # ── Persist dataset metadata ──────────────────────────────────────────
    dataset = Dataset(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=file.filename,
        source_type="csv",
        storage_ref=file.filename,
        table_name=table_name,
        schema_json=schema_preview.model_dump_json(),
        row_count=schema_preview.row_count,
        created_at=datetime.utcnow(),
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return DatasetUploadResponse(
        id=dataset.id,
        user_id=dataset.user_id,
        name=dataset.name,
        source_type=dataset.source_type,
        table_name=table_name,
        row_count=schema_preview.row_count,
        schema_preview=schema_preview,
        created_at=dataset.created_at,
    )


@router.get(
    "/",
    response_model=list[DatasetListItem],
    summary="List all datasets belonging to the current user.",
)
def list_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DatasetListItem]:
    rows = (
        db.query(Dataset)
        .filter(Dataset.user_id == current_user.id)
        .order_by(Dataset.created_at.desc())
        .all()
    )
    return [
        DatasetListItem(
            id=d.id,
            name=d.name,
            source_type=d.source_type,
            row_count=d.row_count,
            created_at=d.created_at,
        )
        for d in rows
    ]


@router.get(
    "/{dataset_id}",
    response_model=DatasetUploadResponse,
    summary="Retrieve a single dataset with its full schema preview.",
)
def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetUploadResponse:
    dataset = (
        db.query(Dataset)
        .filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id)
        .first()
    )
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    schema_preview = SchemaPreview.model_validate_json(dataset.schema_json)

    return DatasetUploadResponse(
        id=dataset.id,
        user_id=dataset.user_id,
        name=dataset.name,
        source_type=dataset.source_type,
        table_name=dataset.table_name,
        row_count=dataset.row_count,
        schema_preview=schema_preview,
        created_at=dataset.created_at,
    )
