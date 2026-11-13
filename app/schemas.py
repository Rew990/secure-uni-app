from pydantic import BaseModel, Field

from app.roles import Role


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: str | None = Field(default=None, description="6-digit code, once MFA is enabled")


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8)
    role: Role


class UserOut(BaseModel):
    id: int
    username: str
    role: Role
    mfa_enabled: bool

    model_config = {"from_attributes": True}


class StudentBase(BaseModel):
    student_number: str
    full_name: str
    birth_year: int = Field(ge=1900, le=2100)
    gender: str
    zip_code: str
    department: str
    gpa: float = Field(ge=0, le=4)


class StudentCreate(StudentBase):
    national_id: str | None = None  # plaintext in, encrypted before storage


class StudentOut(StudentBase):
    id: int

    model_config = {"from_attributes": True}


class GradeUpdate(BaseModel):
    gpa: float = Field(ge=0, le=4)


class AnonymizedOut(BaseModel):
    age_range: str
    gender: str
    zip_prefix: str
    department: str
    gpa: float

    model_config = {"from_attributes": True}
