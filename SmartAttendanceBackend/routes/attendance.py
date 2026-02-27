from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Student, AttendanceRecord, StatusEnum
from schemas import AttendanceOut
from services.face_recognition import match_face
from datetime import date
import shutil, os, uuid

router = APIRouter(prefix="/attendance", tags=["Attendance"])

TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

@router.post("/scan")
async def scan_face(face_image: UploadFile = File(...), db: Session = Depends(get_db)):
    # Save temp image
    temp_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.jpg")
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(face_image.file, f)

    try:
        roll = match_face(temp_path, "known_faces")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    if not roll:
        raise HTTPException(status_code=404, detail="Face not recognized")

    student = db.query(Student).filter(Student.roll == roll).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found in DB")

    today = str(date.today())

    # Prevent duplicate marking
    already = db.query(AttendanceRecord).filter(
        AttendanceRecord.student_id == student.id,
        AttendanceRecord.session_date == today
    ).first()

    if already:
        return {"message": "Already marked", "student": student.name, "status": already.status}

    record = AttendanceRecord(
        student_id=student.id,
        status=StatusEnum.present,
        session_date=today
    )
    db.add(record)
    db.commit()

    return {
        "message": "Attendance marked",
        "student": student.name,
        "roll": student.roll,
        "status": "present"
    }

@router.post("/mark-absent/{student_id}")
def mark_absent(student_id: int, db: Session = Depends(get_db)):
    today = str(date.today())
    existing = db.query(AttendanceRecord).filter(
        AttendanceRecord.student_id == student_id,
        AttendanceRecord.session_date == today
    ).first()
    if existing:
        existing.status = StatusEnum.absent
        db.commit()
        return {"message": "Updated to absent"}

    record = AttendanceRecord(
        student_id=student_id,
        status=StatusEnum.absent,
        session_date=today
    )
    db.add(record)
    db.commit()
    return {"message": "Marked absent"}

@router.get("/today", response_model=list[AttendanceOut])
def get_today_attendance(db: Session = Depends(get_db)):
    today = str(date.today())
    return db.query(AttendanceRecord).filter(AttendanceRecord.session_date == today).all()