"""
Audit log — append-only, no delete endpoint.
POST /api/audit-logs — used by persist_audit_tool
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import Field

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models.agents import AuditLog
from models.user import User

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


class AuditLogCreate(BaseModel):
    action: str
    entity_type: str = ""
    entity_id: str = ""
    metadata: Dict[str, Any] = {}
    user_id: Optional[int] = None  # tool layer may specify the affected user


class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    entity_type: str
    entity_id: str
    metadata: Dict[str, Any] = Field(alias="meta", serialization_alias="metadata")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


@router.post("", response_model=AuditLogOut, status_code=201)
async def create_audit_log(
    body: AuditLogCreate,
    caller: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    log = AuditLog(
        user_id=body.user_id if body.user_id is not None else caller.id,
        action=body.action,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        meta=body.metadata,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log
