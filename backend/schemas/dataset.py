from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class ColumnProfile(BaseModel):
    """Profile for a single column in the uploaded CSV."""

    name: str
    inferred_type: str  # integer | float | boolean | datetime | string
    null_percentage: float  # 0.0 – 100.0
    sample_values: List[Any]  # up to 3 non-null values


class SchemaPreview(BaseModel):
    """Full schema preview returned immediately after CSV upload."""

    table_name: str
    row_count: int
    columns: List[ColumnProfile]


class DatasetUploadResponse(BaseModel):
    """Response body for POST /datasets/upload."""

    id: str
    user_id: str
    name: str
    source_type: str
    table_name: str
    row_count: int
    schema_preview: SchemaPreview
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetListItem(BaseModel):
    """Compact representation used in list endpoints."""

    id: str
    name: str
    source_type: str
    row_count: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}
