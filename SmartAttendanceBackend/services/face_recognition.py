import face_recognition
import numpy as np
import os

def encode_face(image_path):
    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)
    if encodings:
        return encodings[0].tolist()
    return None

def match_face(unknown_image_path, known_faces_dir):
    unknown_image = face_recognition.load_image_file(unknown_image_path)
    unknown_encodings = face_recognition.face_encodings(unknown_image)
    
    if not unknown_encodings:
        return None
    
    unknown_encoding = unknown_encodings[0]
    
    for filename in os.listdir(known_faces_dir):
        if filename.endswith(('.jpg', '.jpeg', '.png')):
            known_path = os.path.join(known_faces_dir, filename)
            known_image = face_recognition.load_image_file(known_path)
            known_encodings = face_recognition.face_encodings(known_image)
            
            if known_encodings:
                match = face_recognition.compare_faces([known_encodings[0]], unknown_encoding, tolerance=0.6)
                if match[0]:
                    return filename.split('.')[0]  # return roll number
    return None