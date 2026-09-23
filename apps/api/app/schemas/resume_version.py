from datetime import datetime

from pydantic import BaseModel


class ResumeFileVersionOut(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int | None
    sha256: str | None
    version: int
    uploaded_at: datetime
    archived_at: datetime
    is_current: bool = False


class ResumeFileMetaOut(BaseModel):
    id: str | None
    filename: str
    content_type: str
    size_bytes: int | None
    sha256: str | None
    version: int
    uploaded_at: datetime
