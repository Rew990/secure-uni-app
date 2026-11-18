"""Anonymised dataset (owner: Privacy, served by Core app).

GET  /anonymized         admin, instructor
POST /anonymized/import  admin only: replaces the table with anonymised.csv
"""
import csv
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AnonymizedRecord
from app.roles import Role
from app.schemas import AnonymizedOut
from app.security.rbac import get_db, require_role

router = APIRouter(prefix="/anonymized", tags=["anonymized"])

CSV_PATH = Path("anonymization/output/anonymised.csv")
COLUMNS = ["age_range", "gender", "zip_prefix", "department", "gpa"]


@router.get("", response_model=list[AnonymizedOut],
            dependencies=[Depends(require_role(Role.ADMIN, Role.INSTRUCTOR))])
def list_anonymized(db: Session = Depends(get_db)) -> list[AnonymizedRecord]:
    return list(db.scalars(select(AnonymizedRecord).order_by(AnonymizedRecord.id)))


@router.post("/import", dependencies=[Depends(require_role(Role.ADMIN))])
def import_anonymized(db: Session = Depends(get_db)) -> dict:
    if not CSV_PATH.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run the k-anonymity script first")
    with CSV_PATH.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or list(rows[0].keys()) != COLUMNS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"CSV must have columns {COLUMNS}")

    db.execute(delete(AnonymizedRecord))          # replace, don't append
    db.add_all(AnonymizedRecord(**{**r, "gpa": float(r["gpa"])}) for r in rows)
    db.commit()
    return {"imported": len(rows)}