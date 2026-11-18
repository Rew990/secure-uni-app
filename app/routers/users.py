"""User management, admin only (owner: Core app / RBAC)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.roles import Role
from app.schemas import UserCreate, UserOut
from app.security.passwords import hash_password
from app.security.rbac import get_db, require_role
from app.models import Material, Student, User
from app.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_role(Role.ADMIN))])

def find_student_id(db: Session, role: Role, student_number: str | None) -> int | None:
    """A student account must point to a student record; other roles must not."""
    if role != Role.STUDENT:
        if student_number:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only student accounts have a student number")
        return None
    if not student_number:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A student account needs a student_number")
    student = db.scalar(select(Student).where(Student.student_number == student_number))
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No student with that student number")
    return student.id


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user

@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already exists")
    student_id = find_student_id(db, body.role, body.student_number)
    user = User(username=body.username, password_hash=hash_password(body.password), role=body.role, student_id=student_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate,
                admin: User = Depends(require_role(Role.ADMIN)),
                db: Session = Depends(get_db)) -> User:
    # 1. load the user, and see which fields the admin actually sent
    user = get_user_or_404(db, user_id)
    changes = body.model_dump(exclude_unset=True)

    # 2. the admin can't take away their own admin role
    if "role" in changes and user.id == admin.id and body.role != Role.ADMIN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot remove your own admin role")

    # 3. new username, if it isn't taken
    if body.username is not None and body.username != user.username:
        if db.scalar(select(User).where(User.username == body.username)):
            raise HTTPException(status.HTTP_409_CONFLICT, "Username already exists")
        user.username = body.username

    # 4. password reset: store only the hash
    if body.password is not None:
        user.password_hash = hash_password(body.password)

    # 5. new role and/or student number
    if "role" in changes or "student_number" in changes:
        new_role = body.role or user.role
        number = changes.get("student_number")
        if number is None and new_role == Role.STUDENT and user.student_id:
            number = db.get(Student, user.student_id).student_number   # keep the current link
        user.student_id = find_student_id(db, new_role, number)
        user.role = new_role

    # 6. save
    db.commit()
    db.refresh(user)
    return user
