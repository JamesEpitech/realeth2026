"""Traitement de l'iris : segmentation, normalisation, encodage IrisCode."""

import numpy as np
import cv2

from config import IRISCODE_BITS


def detect_pupil_iris(image: np.ndarray) -> tuple[tuple, tuple] | None:
    """Detecte les cercles de la pupille et de l'iris via Hough Transform.

    Retourne ((px, py, pr), (ix, iy, ir)) ou None si echec.
    - (px, py, pr) = centre et rayon de la pupille
    - (ix, iy, ir) = centre et rayon de l'iris
    """
    blurred = cv2.GaussianBlur(image, (7, 7), 0)

    # Detection pupille (cercle sombre, petit rayon)
    pupils = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=100,
        param1=100,
        param2=40,
        minRadius=20,
        maxRadius=80,
    )

    if pupils is None:
        return None

    px, py, pr = np.round(pupils[0][0]).astype(int)

    # Detection iris (cercle plus grand autour de la pupille)
    iris_circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=100,
        param1=100,
        param2=35,
        minRadius=pr + 20,
        maxRadius=pr * 4,
    )

    if iris_circles is None:
        return None

    ix, iy, ir = np.round(iris_circles[0][0]).astype(int)

    return (px, py, pr), (ix, iy, ir)


def normalize_iris(
    image: np.ndarray,
    pupil: tuple[int, int, int],
    iris: tuple[int, int, int],
    radial_res: int = 64,
    angular_res: int = 512,
) -> np.ndarray:
    """Normalise l'iris en coordonnees polaires (Daugman rubber sheet model).

    Retourne une image 2D (radial_res x angular_res) representant l'iris deplie.
    """
    px, py, pr = pupil
    ix, iy, ir = iris

    normalized = np.zeros((radial_res, angular_res), dtype=np.uint8)
    thetas = np.linspace(0, 2 * np.pi, angular_res, endpoint=False)

    for j, theta in enumerate(thetas):
        for i in range(radial_res):
            r = i / radial_res
            x = int((1 - r) * (px + pr * np.cos(theta)) + r * (ix + ir * np.cos(theta)))
            y = int((1 - r) * (py + pr * np.sin(theta)) + r * (iy + ir * np.sin(theta)))

            if 0 <= x < image.shape[1] and 0 <= y < image.shape[0]:
                normalized[i, j] = image[y, x]

    return normalized


def encode_iriscode(normalized_iris: np.ndarray) -> np.ndarray:
    """Encode l'iris normalise en IrisCode via filtres de Gabor 2D.

    Retourne un vecteur binaire de IRISCODE_BITS bits sous forme de bytes.
    """
    num_filters = 8
    bits_per_filter = IRISCODE_BITS // num_filters
    iriscode = []

    for k in range(num_filters):
        theta = k * np.pi / num_filters
        kernel = cv2.getGaborKernel(
            ksize=(31, 31),
            sigma=4.0,
            theta=theta,
            lambd=10.0,
            gamma=0.5,
            psi=0,
        )
        filtered = cv2.filter2D(normalized_iris, cv2.CV_64F, kernel)

        # Echantillonnage regulier pour extraire les bits
        flat = filtered.flatten()
        indices = np.linspace(0, len(flat) - 1, bits_per_filter, dtype=int)
        bits = (flat[indices] > 0).astype(np.uint8)
        iriscode.extend(bits)

    iriscode = np.array(iriscode[:IRISCODE_BITS], dtype=np.uint8)
    return np.packbits(iriscode)


def hamming_distance(code1: bytes, code2: bytes) -> float:
    """Calcule la distance de Hamming normalisee entre deux IrisCodes.

    Retourne un float entre 0.0 (identique) et 1.0 (completement different).
    """
    a = np.unpackbits(np.frombuffer(code1, dtype=np.uint8))
    b = np.unpackbits(np.frombuffer(code2, dtype=np.uint8))

    min_len = min(len(a), len(b))
    a, b = a[:min_len], b[:min_len]

    return np.sum(a != b) / min_len
