from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.security.rbac import get_db
from app.models import Material, User
from app.roles import Role
from app.security.rbac import get_current_user, require_role

router = APIRouter(prefix="/materials", tags=["materials"])

UPLOAD_DIR = Path("data/materials")
ALLOWED = {".pdf", ".pptx", ".docx"}
MAX_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("", status_code=201,
             dependencies=[Depends(require_role(Role.INSTRUCTOR))])
async def upload_material(
    title: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, "Only PDF, PPTX or DOCX")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored = uuid4().hex + ext
    (UPLOAD_DIR / stored).write_bytes(data)

    m = Material(title=title, stored_name=stored,
                 original_name=file.filename, uploaded_by=user.id)
    db.add(m)
    db.commit()
    return {"id": m.id, "title": m.title}


@router.get("", dependencies=[Depends(require_role(Role.INSTRUCTOR, Role.STUDENT))])
def list_materials(db: Session = Depends(get_db)):
    rows = db.query(Material).order_by(Material.uploaded_at.desc()).all()
    return [{"id": m.id, "title": m.title, "uploaded_by": m.uploaded_by,
             "uploaded_at": m.uploaded_at} for m in rows]


@router.get("/{material_id}/download",
            dependencies=[Depends(require_role(Role.INSTRUCTOR, Role.STUDENT))])
def download_material(material_id: int, db: Session = Depends(get_db)):
    m = db.get(Material, material_id)
    if m is None:
        raise HTTPException(404, "Not found")
    return FileResponse(UPLOAD_DIR / m.stored_name, filename=m.original_name)