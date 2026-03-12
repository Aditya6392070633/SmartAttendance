from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes import students, attendance

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Attendance API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(students.router)
app.include_router(attendance.router)

@app.get("/")
def root():
    return {"status": "FaceTrack Backend Running"}
