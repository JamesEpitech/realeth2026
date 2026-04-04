"""Capture d'image iris via la camera avec detection automatique de l'oeil."""

import cv2
import numpy as np
import os

import config

# Charger le classificateur Haar pour la detection des yeux
_CASCADE_PATH = os.path.join(
    cv2.data.haarcascades, "haarcascade_eye.xml"
)
_eye_cascade = cv2.CascadeClassifier(_CASCADE_PATH)

# Seuils de qualite
MIN_CONTRAST = 30.0     # ecart-type minimum des pixels
MIN_SHARPNESS = 50.0    # score Laplacien minimum (flou si trop bas)
MIN_BRIGHTNESS = 40     # moyenne de pixels minimum
MAX_BRIGHTNESS = 220    # moyenne de pixels maximum


def list_cameras(max_index: int = 10) -> list[dict]:
    """Scanne les devices camera disponibles (index 0 a max_index).

    Retourne une liste de dicts avec l'index et les infos de chaque camera.
    """
    cameras = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            backend = cap.getBackendName()
            cameras.append({
                "index": i,
                "resolution": f"{w}x{h}",
                "fps": fps,
                "backend": backend,
                "active": i == config.CAMERA_INDEX,
            })
            cap.release()
    return cameras


def is_camera_available() -> bool:
    """Verifie si la camera active est accessible."""
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    available = cap.isOpened()
    cap.release()
    return available


def compute_quality_score(image: np.ndarray) -> dict:
    """Evalue la qualite d'une image d'oeil.

    Retourne un dict avec les metriques et un booleen 'acceptable'.
    """
    brightness = float(np.mean(image))
    contrast = float(np.std(image))
    sharpness = float(cv2.Laplacian(image, cv2.CV_64F).var())

    acceptable = (
        contrast >= MIN_CONTRAST
        and sharpness >= MIN_SHARPNESS
        and MIN_BRIGHTNESS <= brightness <= MAX_BRIGHTNESS
    )

    return {
        "brightness": round(brightness, 1),
        "contrast": round(contrast, 1),
        "sharpness": round(sharpness, 1),
        "acceptable": acceptable,
    }


def detect_best_eye(gray_frame: np.ndarray) -> np.ndarray | None:
    """Detecte les yeux dans l'image et retourne le crop du plus grand oeil.

    Utilise le Haar Cascade haarcascade_eye.xml.
    Retourne l'image croppee en niveaux de gris ou None si aucun oeil detecte.
    """
    eyes = _eye_cascade.detectMultiScale(
        gray_frame,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(40, 40),
    )

    if len(eyes) == 0:
        return None

    # Prendre l'oeil avec la plus grande surface (le plus net / proche)
    largest = max(eyes, key=lambda e: e[2] * e[3])
    x, y, w, h = largest

    # Ajouter une marge de 20% autour de l'oeil pour garder le contexte iris
    margin_x = int(w * 0.2)
    margin_y = int(h * 0.2)
    x1 = max(0, x - margin_x)
    y1 = max(0, y - margin_y)
    x2 = min(gray_frame.shape[1], x + w + margin_x)
    y2 = min(gray_frame.shape[0], y + h + margin_y)

    return gray_frame[y1:y2, x1:x2]


def capture_eye_image() -> tuple[np.ndarray | None, dict, list[np.ndarray]]:
    """Capture une image de l'oeil depuis la camera.

    Detecte automatiquement l'oeil, crop dessus, et evalue la qualite.
    Retourne (image_croppee, quality_info, eye_frames) ou (None, quality_info, []) si echec.
    """
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        return None, {"error": f"camera_unavailable (index={config.CAMERA_INDEX})"}, []

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAPTURE_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAPTURE_HEIGHT)

    # Capturer plusieurs frames pour qualite + anti-spoofing (mouvement)
    best_eye = None
    best_score = -1.0
    best_quality = {}
    eye_frames = []

    for _ in range(5):
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        eye_crop = detect_best_eye(gray)

        if eye_crop is None:
            continue

        eye_frames.append(eye_crop)

        quality = compute_quality_score(eye_crop)
        if not quality["acceptable"]:
            continue

        score = quality["sharpness"] + quality["contrast"]
        if score > best_score:
            best_score = score
            best_eye = eye_crop
            best_quality = quality

    cap.release()

    if best_eye is None:
        return None, {"error": "no_eye_detected"}, []

    return best_eye, best_quality, eye_frames
