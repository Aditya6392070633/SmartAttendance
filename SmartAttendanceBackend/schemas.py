from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class StudentCreate(BaseModel):
    name: str
    roll: str
    department: str

class StudentOut(BaseModel):
    id: int
    name: str
    roll: str
    department: str
    class Config:
        from_attributes = True   # ← changed here

class AttendanceOut(BaseModel):
    id: int
    student_id: int
    status: str
    session_date: str
    marked_at: datetime
    class Config:
        from_attributes = True   # ← changed here