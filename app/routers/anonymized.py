"""Anonymised dataset, readable by every role (owner: Privacy, served by Core app)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnonymizedRecord
from app.roles import Role
from app.schemas import AnonymizedOut
from app.security.rbac import get_db, require_role

router = APIRouter(prefix="/anonymized", tags=["anonymized"])


@router.get("", response_model=list[AnonymizedOut],
            dependencies=[Depends(require_role(Role.ADMIN, Role.INSTRUCTOR, Role.STUDENT))])
def list_anonymized(db: Session = Depends(get_db)) -> list[AnonymizedRecord]:
    return list(db.scalars(select(AnonymizedRecord).order_by(AnonymizedRecord.id)))

# TODO(privacy): admin-only POST /anonymized/import that loads anonymization/output/anonymised.csv
