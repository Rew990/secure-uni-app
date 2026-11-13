"""Student records (owner: Core app / RBAC).

admin   -> read + create + change GPA
instructor -> read only
student -> no access (403); uses /anonymized instead
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Student, User
from app.roles import Role
from app.schemas import GradeUpdate, StudentCreate, StudentOut
from app.security import crypto
from app.security.rbac import get_db, require_role, get_current_user

router = APIRouter(prefix="/students", tags=["students"])

read_roles = require_role(Role.ADMIN, Role.INSTRUCTOR)
write_roles = require_role(Role.ADMIN)


@router.get("", response_model=list[StudentOut], dependencies=[Depends(read_roles)])
def list_students(db: Session = Depends(get_db)) -> list[Student]:
    return list(db.scalars(select(Student).order_by(Student.id)))

@router.get("/me", response_model=StudentOut, dependencies=[Depends(require_role(Role.STUDENT))])
def get_current_student(user: User=Depends(get_current_user), db: Session = Depends(get_db)) -> Student:
    student = db.get(Student, user.student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")
    return student

@router.get("/{student_id}", response_model=StudentOut, dependencies=[Depends(read_roles)])
def get_student(student_id: int, db: Session = Depends(get_db)) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")
    return student


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(write_roles)])
def create_student(body: StudentCreate, db: Session = Depends(get_db)) -> Student:
    data = body.model_dump(exclude={"national_id"})
    student = Student(**data)
    if body.national_id:
        try:
            student.national_id_enc = crypto.encrypt_field(body.national_id)
        except NotImplementedError:
            raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Field encryption not implemented yet")
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.patch("/{student_id}/gpa", response_model=StudentOut, dependencies=[Depends(write_roles)])
def update_gpa(student_id: int, body: GradeUpdate, db: Session = Depends(get_db)) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")
    student.gpa = body.gpa
    db.commit()
    db.refresh(student)
    return student
