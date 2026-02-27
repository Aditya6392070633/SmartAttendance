import numpy as np
import os
import cv2

def encode_face(image_path):
    """Encode face using OpenCV - lightweight, no dlib required"""
    try:
        image = cv2.imread(image_path)
        if image is None:
            return None
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        if len(faces) == 0:
            return None
        x, y, w, h = faces[0]
        face_roi = gray[y:y+h, x:x+w]
        face_resized = cv2.resize(face_roi, (128, 128))
        return face_resized.flatten().tolist()
    except Exception as e:
        print(f"Error encoding face: {e}")
        return None

def match_face(unknown_image_path, known_faces_dir="known_faces"):
    """Match face against known faces using OpenCV"""
    try:
        unknown_image = cv2.imread(unknown_image_path)
        if unknown_image is None:
            return None

        gray_unknown = cv2.cvtColor(unknown_image, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        unknown_faces = face_cascade.detectMultiScale(gray_unknown, 1.1, 4)

        if len(unknown_faces) == 0:
            return None

        x, y, w, h = unknown_faces[0]
        unknown_roi = gray_unknown[y:y+h, x:x+w]
        unknown_resized = cv2.resize(unknown_roi, (128, 128))

        if not os.path.exists(known_faces_dir):
            return None

        best_match = None
        best_score = float('inf')

        for filename in os.listdir(known_faces_dir):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                known_path = os.path.join(known_faces_dir, filename)
                known_image = cv2.imread(known_path)

                if known_image is None:
                    continue

                gray_known = cv2.cvtColor(known_image, cv2.COLOR_BGR2GRAY)
                known_faces_detected = face_cascade.detectMultiScale(gray_known, 1.1, 4)

                if len(known_faces_detected) == 0:
                    continue

                kx, ky, kw, kh = known_faces_detected[0]
                known_roi = gray_known[ky:ky+kh, kx:kx+kw]
                known_resized = cv2.resize(known_roi, (128, 128))

                # Compare faces using mean squared error
                diff = np.mean((unknown_resized.astype(float) - known_resized.astype(float)) ** 2)

                if diff < best_score:
                    best_score = diff
                    best_match = filename.split('.')[0]  # return roll number

        # Threshold for match (lower = more strict)
        if best_score < 2000:
            return best_match

        return None

    except Exception as e:
        print(f"Error matching face: {e}")
        return None


def save_face_image(image_bytes, roll: str, known_faces_dir: str = "known_faces"):
    """Save uploaded face image to known_faces directory"""
    os.makedirs(known_faces_dir, exist_ok=True)
    file_path = os.path.join(known_faces_dir, f"{roll}.jpg")
    with open(file_path, "wb") as f:
        f.write(image_bytes)
    return file_path