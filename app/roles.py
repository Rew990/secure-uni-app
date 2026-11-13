from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"      # manage users, create/edit students and grades
    INSTRUCTOR = "instructor"  # reads student records, changes grades, uploads course material
    STUDENT = "student"    # logs in, sees only their own grades, views and downloads course material
