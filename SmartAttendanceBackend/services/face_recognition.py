import numpy as np
import os
import pickle
import cv2

# insightface + onnxruntime — no dlib, no tensorflow, works on Python 3.11
# Install: pip install insightface onnxruntime opencv-python-headless
import insightface
from insightface.app import FaceAnalysis

# ── Config ────────────────────────────────────────────────────────────────
MATCH_THRESHOLD = 0.50   # cosine distance — lower = more similar
CACHE_FILE      = "known_faces/embeddings.pkl"
EMBEDDING_CACHE = {}     # { roll: 512-float embedding }
_app            = None   # lazy-loaded FaceAnalysis model


def _get_app():
    """Load InsightFace model once and reuse."""
    global _app
    if _app is None:
        _app = FaceAnalysis(name="buffalo_sc", providers=["CPUExecutionProvider"])
        _app.prepare(ctx_id=0, det_size=(320, 320))
    return _app


# ── Image normalization (lighting fix) ───────────────────────────────────

def _normalize(image_path: str) -> np.ndarray:
    """
    Load image and fix lighting with CLAHE before embedding.
    CLAHE equalizes brightness so dark/bright photos of the same
    face produce nearly identical pixel values.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")

    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    bgr = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    # InsightFace expects RGB
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def _get_embedding(image_path: str):
    """
    Normalize → detect face → return 512-float ArcFace embedding.
    Returns None if no face detected.
    """
    try:
        img_rgb = _normalize(image_path)
        app = _get_app()
        faces = app.get(img_rgb)
        if not faces:
            print(f"[face_recognition] No face detected: {image_path}")
            return None
        return faces[0].embedding  # 512-float numpy array
    except Exception as e:
        print(f"[face_recognition] Error: {e}")
        return None


def _cosine_distance(a, b) -> float:
    a = np.array(a)
    b = np.array(b)
    return float(1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


# ── Cache helpers ─────────────────────────────────────────────────────────

def _load_cache():
    global EMBEDDING_CACHE
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            EMBEDDING_CACHE = pickle.load(f)


def _save_cache():
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(EMBEDDING_CACHE, f)


# ── Public API ────────────────────────────────────────────────────────────

def encode_face(image_path: str):
    return _get_embedding(image_path)


def save_face_image(image_bytes: bytes, roll: str,
                    known_faces_dir: str = "known_faces") -> str:
    """Save uploaded photo and pre-compute embedding at registration."""
    os.makedirs(known_faces_dir, exist_ok=True)
    file_path = os.path.join(known_faces_dir, f"{roll}.jpg")

    with open(file_path, "wb") as f:
        f.write(image_bytes)

    embedding = _get_embedding(file_path)
    if embedding is not None:
        _load_cache()
        EMBEDDING_CACHE[roll] = embedding
        _save_cache()
        print(f"[face_recognition] Registered roll={roll}")
    else:
        print(f"[face_recognition] WARNING: No face found for roll={roll}")

    return file_path


def match_face(unknown_image_path: str,
               known_faces_dir: str = "known_faces") -> str | None:
    """
    Normalize → embed → compare cosine distance against all known faces.
    Returns roll number of best match, or None.

    Both registration and scan go through the same CLAHE normalization,
    so lighting changes are cancelled out before comparison.
    """
    if not os.path.exists(known_faces_dir):
        return None

    unknown_emb = _get_embedding(unknown_image_path)
    if unknown_emb is None:
        return None

    _load_cache()
    if not EMBEDDING_CACHE:
        _rebuild_cache(known_faces_dir)
    if not EMBEDDING_CACHE:
        return None

    best_roll = None
    best_dist = float("inf")

    for roll, known_emb in EMBEDDING_CACHE.items():
        dist = _cosine_distance(unknown_emb, known_emb)
        print(f"[face_recognition] roll={roll} dist={dist:.4f}")
        if dist < best_dist:
            best_dist = dist
            best_roll = roll

    if best_dist < MATCH_THRESHOLD:
        print(f"[face_recognition] MATCH → roll={best_roll} dist={best_dist:.4f}")
        return best_roll

    print(f"[face_recognition] NO MATCH — best dist={best_dist:.4f}")
    return None


def _rebuild_cache(known_faces_dir: str):
    """Rebuild cache from images on disk (runs once on fresh deploy)."""
    global EMBEDDING_CACHE
    print("[face_recognition] Rebuilding cache from disk...")
    for filename in os.listdir(known_faces_dir):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            roll = filename.rsplit(".", 1)[0]
            path = os.path.join(known_faces_dir, filename)
            emb = _get_embedding(path)
            if emb is not None:
                EMBEDDING_CACHE[roll] = emb
    _save_cache()
    print(f"[face_recognition] Cache ready: {len(EMBEDDING_CACHE)} faces.")
