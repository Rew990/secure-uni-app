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

STUDENT_LOGINS = {
    "S1001": ("ahmed.hassan", "xnJnjpmq@1001"),
    "S1002": ("sara.omar", "9HX5TQm8@1002"),
    "S1003": ("rawan.adam", "4g7k2Lqv@1003"),
    "S1004": ("khalid.ali", "2J8vN3pQ@1004"),
    "S1005": ("yousef.mohammed", "5k9L2mQw@1005"),
    "S1006": ("shaza.hany", "7H3kL9pQ@1006"),
    "S1007": ("karim.saad", "3J8vN2pQ@1007"),
    "S1008": ("mohammed.khalil", "6k9L3mQw@1008"),
    "S1009": ("mariam.adel", "8H3kL1pQ@1009"),
    "S1010": ("nour.khaled", "1J8vN4pQ@1010"),
    "S1011": ("mostafa.salah", "4k9L5mQw@1011"),
    "S1012": ("laila.ashraf", "7H3kL2pQ@1012"),
    "S1013": ("jana.hossam", "2J8vN5pQ@1013"),
    "S1014": ("ziad.ashraf", "5k9L6mQw@1014"),
    "S1015": ("amr.nabil", "8H3kL3pQ@1015"),
    "S1016": ("farah.nabil", "1J8vN6pQ@1016"),
    "S1017": ("salma.reda", "4k9L7mQw@1017"),
    "S1018": ("hassan.omer", "7H3kL4pQ@1018"),
    "S1019": ("tamer.magdy", "2J8vN7pQ@1019"),
    "S1020": ("yara.sameh", "5k9L8mQw@1020"),
    "S1021": ("dina.essam", "8H3kL5pQ@1021"),
    "S1022": ("malak.fathy", "1J8vN8pQ@1022"),
    "S1023": ("ahmed.samir", "4k9L9mQw@1023"),
    "S1024": ("remas.adel", "7H3kL6pQ@1024"),
    "S1025": ("hamada.hamada", "2J8vN9pQ@1025"),
    }
def seed() -> None:
    db = new_session()
    try:
        for s in DEMO_STUDENTS:
            if not db.scalar(select(Student).where(Student.student_number == s["student_number"])):
                db.add(Student(**s))
        db.commit()  # students need ids before a user can point to one

        # loop 1: admin, instructor, student (unchanged)
        for username, password, role, student_number in DEMO_USERS:
            if db.scalar(select(User).where(User.username == username)):
                continue
            student = None
            if student_number:
                student = db.scalar(select(Student).where(Student.student_number == student_number))
            db.add(User(username=username, password_hash=hash_password(password), role=role,
                        student_id=student.id if student else None))

        # loop 2 (new): one login per student
        for number, (username, password) in STUDENT_LOGINS.items():
            if db.scalar(select(User).where(User.username == username)):
                continue
            student = db.scalar(select(Student).where(Student.student_number == number))
            db.add(User(username=username, password_hash=hash_password(password),
                        role=Role.STUDENT, student_id=student.id))

        db.commit()
    finally:
        db.close()
