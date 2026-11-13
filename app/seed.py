"""Demo data for development. Never enable SEED_DEMO_USERS in production."""
from sqlalchemy import select

from app.database import new_session
from app.models import Student, User
from app.roles import Role
from app.security.passwords import hash_password

DEMO_USERS = [
    ("admin", "Admin@12345", Role.ADMIN, None),
    ("instructor", "Instructor@12345", Role.INSTRUCTOR, None),
    ("student", "Student@12345", Role.STUDENT, "S1001"),
]

DEMO_STUDENTS = [
    dict(student_number="S1001", full_name="Ahmed Hassan", birth_year=2003, gender="F", zip_code="11511", department="CS", gpa=3.4),
    dict(student_number="S1002", full_name="Sara Omar", birth_year=2002, gender="F", zip_code="11835", department="AI", gpa=2.9),
    dict(student_number="S1003", full_name="Rawan Adam", birth_year=2004, gender="F", zip_code="11728", department="IS", gpa=4.0),
    dict(student_number="S1004", full_name="Khalid Ali", birth_year=2003, gender="M", zip_code="11562", department="CN", gpa=2.9),
    dict(student_number="S1005", full_name="Yousef Mohammed", birth_year=2002, gender="M", zip_code="11645", department="CS", gpa=3.0),
    dict(student_number="S1006", full_name="Shaza Hany", birth_year=2005, gender="F", zip_code="11817", department="AI", gpa=4.0),
    dict(student_number="S1007", full_name="Karim Saad", birth_year=2003, gender="M", zip_code="11828", department="SE", gpa=3.5),
    dict(student_number="S1008", full_name="Mohammed Khalil", birth_year=2003, gender="M", zip_code="11532", department="CN", gpa=3.5),
    dict(student_number="S1009", full_name="Mariam Adel", birth_year=2002, gender="F", zip_code="11739", department="SE", gpa=2.8),
    dict(student_number="S1010", full_name="Nour Khaled", birth_year=2002, gender="F", zip_code="11861", department="IS", gpa=4.0),
    dict(student_number="S1011", full_name="Mostafa Salah", birth_year=2004, gender="M", zip_code="11765", department="IS", gpa=2.9),
    dict(student_number="S1012", full_name="Laila Ashraf", birth_year=2003, gender="F", zip_code="11932", department="AI", gpa=2.3),
    dict(student_number="S1013", full_name="Jana Hossam", birth_year=2002, gender="F", zip_code="11849", department="CN", gpa=3.3),
    dict(student_number="S1014", full_name="Ziad Ashraf", birth_year=2004, gender="M", zip_code="11938", department="CN", gpa=3.6),
    dict(student_number="S1015", full_name="Amr Nabil", birth_year=2005, gender="M", zip_code="11843", department="IS", gpa=3.2),
    dict(student_number="S1016", full_name="Farah Nabil", birth_year=2004, gender="F", zip_code="11514", department="SE", gpa=2.1),
    dict(student_number="S1017", full_name="Salma Reda", birth_year=2003, gender="F", zip_code="11462", department="CN", gpa=2.5),
    dict(student_number="S1018", full_name="Hassan Omer", birth_year=2002, gender="M", zip_code="11134", department="CS", gpa=3.4),
    dict(student_number="S1019", full_name="Tamer Magdy", birth_year=2004, gender="M", zip_code="11242", department="AI", gpa=3.1),
    dict(student_number="S1020", full_name="Yara Sameh", birth_year=2004, gender="F", zip_code="11837", department="SE", gpa=1.9),
    dict(student_number="S1021", full_name="Dina Essam", birth_year=2004, gender="F", zip_code="11421", department="CN", gpa=3.0),
    dict(student_number="S1022", full_name="Malak Fathy", birth_year=2002, gender="F", zip_code="11524", department="CN", gpa=3.9),
    dict(student_number="S1023", full_name="Ahmed Samir", birth_year=2003, gender="M", zip_code="11622", department="CS", gpa=2.6),
    dict(student_number="S1024", full_name="Remas Adel", birth_year=2002, gender="F", zip_code="11992", department="AI", gpa=2.2),
    dict(student_number="S1025", full_name="Hamada Hamada", birth_year=2004, gender="M", zip_code="11580", department="CN", gpa=3.1),
]


def seed() -> None:
    db = new_session()
    try:
        for s in DEMO_STUDENTS:
            if not db.scalar(select(Student).where(Student.student_number == s["student_number"])):
                db.add(Student(**s))
        db.commit()  # students need ids before a user can point to one

        for username, password, role, student_number in DEMO_USERS:
            if db.scalar(select(User).where(User.username == username)):
                continue
            student = None
            if student_number:
                student = db.scalar(select(Student).where(Student.student_number == student_number))
            db.add(User(username=username, password_hash=hash_password(password), role=role,
                        student_id=student.id if student else None))
        db.commit()
    finally:
        db.close()
