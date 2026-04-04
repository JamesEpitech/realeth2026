"""Anti-spoofing : detection de vivacite pour rejeter les faux iris."""

import cv2
import numpy as np


# --- Seuils ---
MIN_SPECULAR_SPOTS = 1          # au moins 1 reflet corneen attendu
SPECULAR_THRESHOLD = 250        # intensite pixel pour detecter un reflet IR
MIN_PUPIL_MOVEMENT = 0.3        # deplacement minimum du centre pupille (pixels) entre frames
MAX_PUPIL_MOVEMENT = 15.0       # deplacement maximum (trop = faux mouvement)
LBP_VARIANCE_THRESHOLD = 20.0   # variance LBP minimum (une image imprimee est trop uniforme)


def check_specular_reflection(eye_image: np.ndarray) -> dict:
    """Detecte la reflexion speculaire de la cornee (point lumineux IR).

    Un vrai oeil sous eclairage IR produit un reflet brillant sur la cornee.
    Une photo imprimee ou un ecran ne produit pas ce reflet ponctuel.
    """
    _, bright_mask = cv2.threshold(eye_image, SPECULAR_THRESHOLD, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filtrer les contours trop grands (ce ne sont pas des reflets ponctuels)
    spots = [c for c in contours if cv2.contourArea(c) < 200]

    return {
        "passed": len(spots) >= MIN_SPECULAR_SPOTS,
        "specular_spots": len(spots),
    }


def check_pupil_movement(frames: list[np.ndarray]) -> dict:
    """Detecte les micro-mouvements pupillaires entre plusieurs frames.

    Un vrai oeil a des micro-saccades involontaires. Une photo est statique.
    Necessite au moins 2 frames.
    """
    if len(frames) < 2:
        return {"passed": False, "reason": "not_enough_frames"}

    centers = []
    for frame in frames:
        blurred = cv2.GaussianBlur(frame, (7, 7), 0)
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=50,
            param1=100,
            param2=40,
            minRadius=10,
            maxRadius=80,
        )
        if circles is not None:
            x, y, _ = circles[0][0]
            centers.append((float(x), float(y)))

    if len(centers) < 2:
        return {"passed": False, "reason": "pupil_not_tracked"}

    # Calculer le deplacement total entre frames consecutifs
    total_movement = 0.0
    for i in range(1, len(centers)):
        dx = centers[i][0] - centers[i - 1][0]
        dy = centers[i][1] - centers[i - 1][1]
        total_movement += np.sqrt(dx * dx + dy * dy)

    avg_movement = total_movement / (len(centers) - 1)

    return {
        "passed": MIN_PUPIL_MOVEMENT <= avg_movement <= MAX_PUPIL_MOVEMENT,
        "avg_movement": round(avg_movement, 3),
    }


def _local_binary_pattern(image: np.ndarray) -> np.ndarray:
    """Calcule un LBP simplifie (8 voisins, rayon 1)."""
    h, w = image.shape
    lbp = np.zeros((h - 2, w - 2), dtype=np.uint8)
    for i in range(1, h - 1):
        for j in range(1, w - 1):
            center = image[i, j]
            code = 0
            code |= (image[i - 1, j - 1] >= center) << 7
            code |= (image[i - 1, j]     >= center) << 6
            code |= (image[i - 1, j + 1] >= center) << 5
            code |= (image[i, j + 1]     >= center) << 4
            code |= (image[i + 1, j + 1] >= center) << 3
            code |= (image[i + 1, j]     >= center) << 2
            code |= (image[i + 1, j - 1] >= center) << 1
            code |= (image[i, j - 1]     >= center) << 0
            lbp[i - 1, j - 1] = code
    return lbp


def check_texture_liveness(eye_image: np.ndarray) -> dict:
    """Analyse la texture via LBP pour distinguer un vrai oeil d'une image imprimee/ecran.

    Un vrai iris a une texture riche (haute variance LBP).
    Une photo imprimee ou un ecran a une texture plus lisse/uniforme.
    """
    lbp = _local_binary_pattern(eye_image)
    variance = float(np.var(lbp))

    return {
        "passed": variance >= LBP_VARIANCE_THRESHOLD,
        "lbp_variance": round(variance, 2),
    }


def run_liveness_check(eye_image: np.ndarray, frames: list[np.ndarray] | None = None) -> dict:
    """Execute tous les checks anti-spoofing et retourne un verdict global.

    Args:
        eye_image: image croppee de l'oeil (pour specular + texture)
        frames: liste de frames successifs (pour mouvement pupillaire)

    Retourne un dict avec le resultat de chaque check et le verdict global.
    """
    specular = check_specular_reflection(eye_image)
    texture = check_texture_liveness(eye_image)

    movement = {"passed": True, "skipped": True}
    if frames and len(frames) >= 2:
        movement = check_pupil_movement(frames)

    alive = specular["passed"] and texture["passed"] and movement["passed"]

    return {
        "alive": alive,
        "specular": specular,
        "texture": texture,
        "movement": movement,
    }
