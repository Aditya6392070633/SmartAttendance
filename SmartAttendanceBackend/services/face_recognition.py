import os
import shutil
from deepface import DeepFace
from fastapi import UploadFile

KNOWN_FACES_DIR = "known_faces"
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

def save_face_image(roll: str, file: UploadFile) -> str:
    """Save uploaded face image to disk."""
    path = os.path.join(KNOWN_FACES_DIR, f"{roll}.jpg")
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return path

def recognize_face(uploaded_image_path: str) -> dict:
    """
    Compare uploaded face against all known faces.
    Returns matched student roll number or None.
    """
    best_match = None
    best_distance = float("inf")

    for filename in os.listdir(KNOWN_FACES_DIR):
        known_path = os.path.join(KNOWN_FACES_DIR, filename)
        try:
            result = DeepFace.verify(
                img1_path=uploaded_image_path,
                img2_path=known_path,
                model_name="Facenet512",
                enforce_detection=True
            )
            if result["verified"] and result["distance"] < best_distance:
                best_distance = result["distance"]
                best_match = filename.replace(".jpg", "")  # roll number
        except Exception:
            continue  # face not detected or mismatch

    return {"roll": best_match, "confidence": round(1 - best_distance, 4) if best_match else None}