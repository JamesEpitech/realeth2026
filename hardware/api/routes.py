"""Routes API REST pour le hardware iris."""

import threading
import base64

import cv2
import numpy as np
from flask import Blueprint, jsonify, request

import config
from iris.capture import is_camera_available, capture_eye_image, detect_best_eye, compute_quality_score, list_cameras
from iris.processing import detect_pupil_iris, normalize_iris, encode_iriscode, hamming_distance
from iris.antispoofing import run_liveness_check
from utils.crypto import generate_key, encrypt_template, decrypt_template
from config import MATCH_THRESHOLD, AES_SHARED_KEY

api = Blueprint("api", __name__)

# Cle AES persistante — chargee depuis env ou generee une fois et affichee
if AES_SHARED_KEY:
    _encryption_key = base64.b64decode(AES_SHARED_KEY)
else:
    _encryption_key = generate_key()
    print(f"[CRYPTO] Aucune IRIS_AES_KEY trouvee, cle generee :")
    print(f"[CRYPTO] export IRIS_AES_KEY={base64.b64encode(_encryption_key).decode()}")
    print(f"[CRYPTO] Partagez cette cle avec le backend (P3) pour le dechiffrement.")

# Lock pour eviter les acces concurrents a la camera
_camera_lock = threading.Lock()

# Stockage en memoire des templates enrolles (nullifier_hash -> template chiffre)
_enrolled_templates: dict[str, dict] = {}


def _do_scan():
    """Pipeline interne : capture + liveness + segmentation + encode + chiffre.

    Retourne (response_dict, http_status_code).
    """
    with _camera_lock:
        image, quality, eye_frames = capture_eye_image()

    if image is None:
        error = quality.get("error", "Camera capture failed")
        return {"success": False, "error": error, "quality": quality}, 422

    liveness = run_liveness_check(image, frames=eye_frames)
    if not liveness["alive"]:
        return {
            "success": False,
            "error": "Liveness check failed",
            "quality": quality,
            "liveness": liveness,
        }, 403

    circles = detect_pupil_iris(image)
    if circles is None:
        return {
            "success": False,
            "error": "Iris not detected",
            "quality": quality,
            "liveness": liveness,
        }, 422

    pupil, iris = circles
    normalized = normalize_iris(image, pupil, iris)
    iriscode = encode_iriscode(normalized)
    raw_bytes = iriscode.tobytes()
    encrypted = encrypt_template(raw_bytes, _encryption_key)

    return {
        "success": True,
        "template": encrypted,
        "template_raw_hex": raw_bytes.hex(),
        "quality": quality,
        "liveness": liveness,
    }, 200


# ============================================================
#  GET /status
# ============================================================
@api.route("/status", methods=["GET"])
def status():
    """Verifie l'etat du hardware.

    Response: {
        "server": true,
        "camera": true/false,
        "enrolled_count": 0
    }
    """
    camera_ok = is_camera_available()
    return jsonify({
        "server": True,
        "camera": camera_ok,
        "enrolled_count": len(_enrolled_templates),
    })


# ============================================================
#  POST /scan — retourne un template chiffre (usage libre)
# ============================================================
@api.route("/scan", methods=["POST"])
def scan():
    """Capture un iris et retourne le template chiffre.

    Response: {
        "success": true,
        "template": { "nonce": "...", "ciphertext": "..." },
        "template_raw_hex": "ab01cd...",
        "quality": { ... },
        "liveness": { ... }
    }
    """
    result, code = _do_scan()
    return jsonify(result), code


# ============================================================
#  POST /scan/image — analyse une image envoyee (iPhone, etc.)
# ============================================================
@api.route("/scan/image", methods=["POST"])
def scan_image():
    """Analyse une image d'oeil envoyee par fichier (pas besoin de camera).

    Envoyer via multipart/form-data avec le champ 'image'.
    Ou envoyer du JSON avec le champ 'image_base64' (base64 encoded).

    Exemple curl :
        curl -X POST -F "image=@photo_oeil.jpg" http://localhost:5001/scan/image

    Response: meme format que /scan
    """
    gray = None

    # Option 1 : fichier multipart
    if "image" in request.files:
        file = request.files["image"]
        file_bytes = np.frombuffer(file.read(), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is not None:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Option 2 : base64 dans le JSON
    elif request.is_json and "image_base64" in request.get_json(silent=True):
        data = request.get_json()
        img_bytes = base64.b64decode(data["image_base64"])
        file_bytes = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is not None:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if gray is None:
        return jsonify({"success": False, "error": "No valid image provided. Send 'image' file or 'image_base64' JSON field."}), 400

    # Detecter l'oeil dans l'image
    eye_crop = detect_best_eye(gray)
    if eye_crop is None:
        # Pas d'oeil detecte — utiliser l'image entiere (peut-etre deja un crop d'oeil)
        eye_crop = gray

    quality = compute_quality_score(eye_crop)

    # Liveness (pas de mouvement possible sur une photo)
    liveness = run_liveness_check(eye_crop, frames=None)

    circles = detect_pupil_iris(eye_crop)
    if circles is None:
        return jsonify({
            "success": False,
            "error": "Iris not detected in image",
            "quality": quality,
            "liveness": liveness,
        }), 422

    pupil, iris = circles
    normalized = normalize_iris(eye_crop, pupil, iris)
    iriscode = encode_iriscode(normalized)
    raw_bytes = iriscode.tobytes()
    encrypted = encrypt_template(raw_bytes, _encryption_key)

    return jsonify({
        "success": True,
        "template": encrypted,
        "template_raw_hex": raw_bytes.hex(),
        "quality": quality,
        "liveness": liveness,
    })


# ============================================================
#  POST /enroll — scan + stocke le template de reference
# ============================================================
@api.route("/enroll", methods=["POST"])
def enroll():
    """Scan un iris et stocke le template comme reference pour un utilisateur.

    Body: { "user_id": "nullifier_hash_or_any_id" }
    Response: {
        "success": true,
        "user_id": "...",
        "template": { "nonce": "...", "ciphertext": "..." },
        ...
    }
    """
    data = request.get_json() or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Missing user_id"}), 400

    if user_id in _enrolled_templates:
        return jsonify({"success": False, "error": "User already enrolled"}), 409

    result, code = _do_scan()
    if not result["success"]:
        return jsonify(result), code

    _enrolled_templates[user_id] = result["template"]

    result["user_id"] = user_id
    result["enrolled"] = True
    return jsonify(result), 200


# ============================================================
#  POST /verify — scan + compare avec le template enrole
# ============================================================
@api.route("/verify", methods=["POST"])
def verify():
    """Scan un iris et le compare au template enrole d'un utilisateur.

    Body: { "user_id": "nullifier_hash_or_any_id" }
    Response: {
        "success": true,
        "match": true/false,
        "distance": 0.23,
        "threshold": 0.32,
        ...
    }
    """
    data = request.get_json() or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Missing user_id"}), 400

    if user_id not in _enrolled_templates:
        return jsonify({"success": False, "error": "User not enrolled"}), 404

    result, code = _do_scan()
    if not result["success"]:
        return jsonify(result), code

    # Dechiffrer le template fraichement scanne et celui enrole
    try:
        new_code = decrypt_template(result["template"], _encryption_key)
        ref_code = decrypt_template(_enrolled_templates[user_id], _encryption_key)
    except Exception:
        return jsonify({"success": False, "error": "Decryption failed"}), 500

    distance = hamming_distance(new_code, ref_code)
    matched = distance < MATCH_THRESHOLD

    result["match"] = matched
    result["distance"] = round(float(distance), 4)
    result["threshold"] = MATCH_THRESHOLD
    result["user_id"] = user_id
    return jsonify(result), 200


# ============================================================
#  POST /match — compare deux templates fournis (usage P3/CRE)
# ============================================================
@api.route("/match", methods=["POST"])
def match():
    """Compare deux templates iris et retourne le resultat.

    Body: {
        "template1": { "nonce": "...", "ciphertext": "..." },
        "template2": { "nonce": "...", "ciphertext": "..." }
    }
    Response: {
        "success": true,
        "match": true/false,
        "distance": 0.23,
        "threshold": 0.32
    }
    """
    data = request.get_json()
    if not data or "template1" not in data or "template2" not in data:
        return jsonify({"success": False, "error": "Missing template1 or template2"}), 400

    try:
        code1 = decrypt_template(data["template1"], _encryption_key)
        code2 = decrypt_template(data["template2"], _encryption_key)
    except Exception:
        return jsonify({"success": False, "error": "Decryption failed"}), 400

    distance = hamming_distance(code1, code2)

    return jsonify({
        "success": True,
        "match": distance < MATCH_THRESHOLD,
        "distance": round(float(distance), 4),
        "threshold": MATCH_THRESHOLD,
    })


# ============================================================
#  GET /enrolled — liste les utilisateurs enrolles
# ============================================================
@api.route("/enrolled", methods=["GET"])
def enrolled():
    """Liste les user_id enrolles.

    Response: { "enrolled": ["user1", "user2"], "count": 2 }
    """
    return jsonify({
        "enrolled": list(_enrolled_templates.keys()),
        "count": len(_enrolled_templates),
    })


# ============================================================
#  GET /camera/list — liste les cameras disponibles
# ============================================================
@api.route("/camera/list", methods=["GET"])
def camera_list():
    """Scanne et liste toutes les cameras detectees.

    Response: {
        "cameras": [
            { "index": 0, "resolution": "640x480", "fps": 30, "backend": "V4L2", "active": true },
            { "index": 2, "resolution": "1920x1080", "fps": 30, "backend": "V4L2", "active": false }
        ],
        "active_index": 0
    }
    """
    cameras = list_cameras()
    return jsonify({
        "cameras": cameras,
        "active_index": config.CAMERA_INDEX,
    })


# ============================================================
#  POST /camera/set — change la camera active
# ============================================================
@api.route("/camera/set", methods=["POST"])
def camera_set():
    """Change la camera utilisee pour les scans.

    Body: { "index": 2 }
    Response: { "success": true, "camera_index": 2 }
    """
    data = request.get_json() or {}
    index = data.get("index")

    if index is None or not isinstance(index, int):
        return jsonify({"success": False, "error": "Missing or invalid 'index' (int required)"}), 400

    # Verifier que la camera existe
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        return jsonify({"success": False, "error": f"Camera index {index} not available"}), 404
    cap.release()

    config.CAMERA_INDEX = index
    print(f"[CAMERA] Switched to camera index {index}")

    return jsonify({
        "success": True,
        "camera_index": index,
    })
