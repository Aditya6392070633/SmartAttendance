import numpy as np
import os
import cv2
import pickle

# ── DeepFace for robust, lighting-stable face embeddings ──────────────────
# Install: pip install deepface tf-keras
# DeepFace uses a neural network (Facenet by default) to convert a face into
# a 128-number "fingerprint" that stays stable across lighting changes.
from deepface import DeepFace

EMBEDDING_CACHE = {}   # in-memory cache: roll -> embedding vector
MODEL_NAME      = "Facenet"   # options: "Facenet", "ArcFace", "VGG-Face"
DISTANCE_METRIC = "cosine"    # cosine similarity, range 0.0 (identical) to 1.0
MATCH_THRESHOLD = 0.40        # below 0.40 = same person  (tune if needed)
CACHE_FILE      = "known_faces/embeddings.pkl"


# ── helpers ───────────────────────────────────────────────────────────────

def _load_cache():
    """Load persisted embeddings from disk into memory."""
    global EMBEDDING_CACHE
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            EMBEDDING_CACHE = pickle.load(f)


def _save_cache():
    """Persist in-memory embeddings to disk."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(EMBEDDING_CACHE, f)


def _get_embedding(image_path: str) -> list | None:
    """
    Extract a face embedding vector from an image file.
    Returns None if no face is detected.
    """
    try:
        result = DeepFace.represent(
            img_path      = image_path,
            model_name    = MODEL_NAME,
            enforce_detection = True,   # raise error if no face found
            detector_backend  = "opencv",
        )
        return result[0]["embedding"]   # list of 128 floats
    except Exception as e:
        print(f"[face_recognition] embed error for {image_path}: {e}")
        return None


def _cosine_distance(a: list, b: list) -> float:
    """Lower = more similar. 0.0 = identical."""
    a, b = np.array(a), np.array(b)
    return float(1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


# ── public API (same signatures as original) ──────────────────────────────

def encode_face(image_path: str) -> list | None:
    """
    Extract and return the face embedding for a given image.
    Called during student registration.
    """
    return _get_embedding(image_path)


def save_face_image(image_bytes: bytes, roll: str,
                    known_faces_dir: str = "known_faces") -> str:
    """
    Save uploaded face image and pre-compute + cache its embedding.
    Called during student registration.
    """
    os.makedirs(known_faces_dir, exist_ok=True)
    file_path = os.path.join(known_faces_dir, f"{roll}.jpg")

    with open(file_path, "wb") as f:
        f.write(image_bytes)

    # Pre-compute embedding and cache it
    embedding = _get_embedding(file_path)
    if embedding is not None:
        _load_cache()
        EMBEDDING_CACHE[roll] = embedding
        _save_cache()
        print(f"[face_recognition] Cached embedding for roll={roll}")
    else:
        print(f"[face_recognition] WARNING: No face detected in registration image for roll={roll}")

    return file_path


def match_face(unknown_image_path: str,
               known_faces_dir: str = "known_faces") -> str | None:
    """
    Compare unknown face against all known embeddings.
    Returns the roll number of the best match, or None.

    Why this is lighting-stable:
    - Facenet embeds facial STRUCTURE (bone landmarks, ratios), not pixel values.
    - A dark photo and a bright photo of the same face produce nearly identical
      128-float vectors, so cosine distance stays low regardless of lighting.
    """
    if not os.path.exists(known_faces_dir):
        return None

    # Get embedding for the incoming scan
    unknown_emb = _get_embedding(unknown_image_path)
    if unknown_emb is None:
        print("[face_recognition] No face detected in scan image.")
        return None

    # Load cached embeddings (build cache from disk if missing)
    _load_cache()
    if not EMBEDDING_CACHE:
        _rebuild_cache(known_faces_dir)

    best_roll  = None
    best_dist  = float("inf")

    for roll, known_emb in EMBEDDING_CACHE.items():
        dist = _cosine_distance(unknown_emb, known_emb)
        print(f"[face_recognition] roll={roll}  cosine_dist={dist:.4f}")
        if dist < best_dist:
            best_dist = dist
            best_roll = roll

    if best_dist < MATCH_THRESHOLD:
        print(f"[face_recognition] MATCH → roll={best_roll}  dist={best_dist:.4f}")
        return best_roll

    print(f"[face_recognition] NO MATCH  best_dist={best_dist:.4f} >= threshold={MATCH_THRESHOLD}")
    return None


def _rebuild_cache(known_faces_dir: str):
    """
    Fallback: build embedding cache from raw image files on disk.
    Runs once if embeddings.pkl is missing (e.g. after a fresh deploy).
    """
    global EMBEDDING_CACHE
    print("[face_recognition] Rebuilding embedding cache from disk...")
    for filename in os.listdir(known_faces_dir):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            roll = filename.rsplit(".", 1)[0]
            path = os.path.join(known_faces_dir, filename)
            emb  = _get_embedding(path)
            if emb is not None:
                EMBEDDING_CACHE[roll] = emb
    _save_cache()
    print(f"[face_recognition] Cache built: {len(EMBEDDING_CACHE)} faces.")
