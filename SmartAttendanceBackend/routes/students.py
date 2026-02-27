from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Student
from schemas import StudentOut
from services.face_recognition import save_face_image

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

    face_path = save_face_image(roll, face_image)

    student = Student(name=name, roll=roll, department=department, face_image_path=face_path)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student

@router.get("/", response_model=list[StudentOut])
def get_all_students(db: Session = Depends(get_db)):
    return db.query(Student).all()