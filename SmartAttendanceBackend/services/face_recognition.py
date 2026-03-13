import numpy as np
import os
import pickle
import cv2
import face_recognition

# ── Config ────────────────────────────────────────────────────────────────
MATCH_THRESHOLD = 0.50
CACHE_FILE      = "known_faces/embeddings.pkl"
EMBEDDING_CACHE = {}


# ── Image normalization (THE KEY FIX) ─────────────────────────────────────

def _normalize_image(image_path: str) -> str:
    """
    Fix lighting BEFORE extracting the face embedding.

    Steps:
      1. Convert to LAB color space (separates brightness from color)
      2. Apply CLAHE on the L (brightness) channel only
         - CLAHE = Contrast Limited Adaptive Histogram Equalization
         - Spreads brightness evenly across the face
         - Dark room photo and bright room photo become almost identical
      3. Convert back to RGB and save as a temp file

    Result: same person in dark room vs bright room produces
            nearly identical pixel values -> nearly identical embeddings.
    """
    img = cv2.imread(image_path)
    if img is None:
        return image_path  # fallback to original if unreadable

    # BGR -> LAB
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # Apply CLAHE to L channel only (brightness equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_normalized = clahe.apply(l)

    # Merge back and convert to RGB
    lab_normalized = cv2.merge([l_normalized, a, b])
    rgb = cv2.cvtColor(lab_normalized, cv2.COLOR_LAB2BGR)

    # Save temp normalized image
    temp_path = image_path + "_normalized.jpg"
    cv2.imwrite(temp_path, rgb)
    return temp_path


def _cleanup_temp(path: str):
    if path.endswith("_normalized.jpg") and os.path.exists(path):
        os.remove(path)


# ── Embedding extraction ───────────────────────────────────────────────────

def _get_embedding(image_path: str):
    """
    Normalize image first, then extract 128-float face embedding.
    Returns None if no face is detected.
    """
    normalized_path = _normalize_image(image_path)
    try:
        image = face_recognition.load_image_file(normalized_path)
        encodings = face_recognition.face_encodings(image)
        if not encodings:
            print(f"[face_recognition] No face detected in: {image_path}")
            return None
        return encodings[0]
    finally:
        _cleanup_temp(normalized_path)


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


# ── Public API (same signatures as original) ──────────────────────────────

def encode_face(image_path: str):
    return _get_embedding(image_path)


def save_face_image(image_bytes: bytes, roll: str,
                    known_faces_dir: str = "known_faces") -> str:
    """Save photo + pre-compute normalized embedding at registration time."""
    os.makedirs(known_faces_dir, exist_ok=True)
    file_path = os.path.join(known_faces_dir, f"{roll}.jpg")

    with open(file_path, "wb") as f:
        f.write(image_bytes)

    embedding = _get_embedding(file_path)
    if embedding is not None:
        _load_cache()
        EMBEDDING_CACHE[roll] = embedding
        _save_cache()
        print(f"[face_recognition] Saved normalized embedding for roll={roll}")
    else:
        print(f"[face_recognition] WARNING: No face found for roll={roll}")

    return file_path


def match_face(unknown_image_path: str,
               known_faces_dir: str = "known_faces") -> str | None:
    """
    Normalize scan image -> extract embedding -> compare against all known.
    Both registration and scan go through the same normalization pipeline,
    so lighting differences are cancelled out before any comparison happens.
    """
    if not os.path.exists(known_faces_dir):
        return None

    # Normalize the incoming scan image first
    unknown_emb = _get_embedding(unknown_image_path)
    if unknown_emb is None:
        return None

    _load_cache()
    if not EMBEDDING_CACHE:
        _rebuild_cache(known_faces_dir)
    if not EMBEDDING_CACHE:
        return None

    rolls      = list(EMBEDDING_CACHE.keys())
    known_embs = list(EMBEDDING_CACHE.values())

    distances = face_recognition.face_distance(known_embs, unknown_emb)
    best_idx  = int(np.argmin(distances))
    best_dist = float(distances[best_idx])

    print(f"[face_recognition] Best match: roll={rolls[best_idx]}  dist={best_dist:.4f}")

    if best_dist < MATCH_THRESHOLD:
        return rolls[best_idx]

    print(f"[face_recognition] NO MATCH - dist={best_dist:.4f} >= threshold={MATCH_THRESHOLD}")
    return None


def _rebuild_cache(known_faces_dir: str):
    """Rebuild embedding cache from images on disk (runs once on fresh deploy)."""
    global EMBEDDING_CACHE
    print("[face_recognition] Rebuilding cache...")
    for filename in os.listdir(known_faces_dir):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            roll = filename.rsplit(".", 1)[0]
            path = os.path.join(known_faces_dir, filename)
            emb  = _get_embedding(path)
            if emb is not None:
                EMBEDDING_CACHE[roll] = emb
    _save_cache()
    print(f"[face_recognition] Cache built: {len(EMBEDDING_CACHE)} faces.")
