from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
from database import Base
import enum

class StatusEnum(str, enum.Enum):
    present = "present"
    absent = "absent"

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    roll = Column(String, unique=True, nullable=False)
    department = Column(String)
    face_image_path = Column(String)  # path to stored face image
    created_at = Column(DateTime, server_default=func.now())

class AttendanceRecord(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, nullable=False)
    status = Column(Enum(StatusEnum), nullable=False)
    session_date = Column(String, nullable=False)   # e.g. "2026-02-25"
    marked_at = Column(DateTime, server_default=func.now())