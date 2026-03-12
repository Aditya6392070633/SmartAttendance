from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Student
from schemas import StudentOut
from services.face_recognition import save_face_image
import os

router = APIRouter(prefix="/students", tags=["Students"])

@router.post("/register", response_model=StudentOut)
async def register_student(
    name: str = Form(...),
    roll: str = Form(...),
    department: str = Form(...),
    face_image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    existing = db.query(Student).filter(Student.roll == roll).first()
    if existing:
        raise HTTPException(status_code=400, detail="Student already registered")
    face_bytes = await face_image.read()
    face_path = save_face_image(face_bytes, roll)
    student = Student(name=name, roll=roll, department=department, face_image_path=face_path)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student

@router.get("/", response_model=list[StudentOut])
def get_all_students(db: Session = Depends(get_db)):
    return db.query(Student).all()

@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.face_image_path and os.path.exists(student.face_image_path):
        os.remove(student.face_image_path)
    db.delete(student)
    db.commit()
    return {"message": f"Student {student.name} deleted successfully"}

@router.put("/{student_id}", response_model=StudentOut)
async def update_student(
    student_id: int,
    name: str = Form(None),
    roll: str = Form(None),
    department: str = Form(None),
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if name:
        student.name = name
    if roll:
        student.roll = roll
    if department:
        student.department = department
    db.commit()
    db.refresh(student)
    return student
