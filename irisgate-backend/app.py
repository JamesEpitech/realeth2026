"""IrisGate Backend — API pour enrolement et identification par iris.

Endpoints pour l'extension:
    POST /api/scan      — Capture photo via Pi + identifie l'iris
    POST /api/register  — Enregistre un iris avec un nom de wallet
    GET  /api/accounts  — Liste les comptes

Endpoints directs (image upload):
    POST /enroll    — Inscrit un iris (upload image)
    POST /identify  — Identifie un iris (upload image)

Le template iris est stocke en base (SQLite) pour le matching par Hamming distance.
"""

import os
import sys
import json
import time
import uuid
import tempfile
import sqlite3
import hashlib
import subprocess
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2

# Ajouter iris-recognition au path
IRIS_RECOGNITION_DIR = os.path.join(os.path.dirname(__file__), "..", "iris-recognition")
sys.path.insert(0, IRIS_RECOGNITION_DIR)

from iris_recognition import process_image, compare, get_pipeline, get_matcher, template_to_hash
import numpy as np

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "irisgate.db")
MATCH_THRESHOLD = 0.35

# --- Config Pi ---
PI_USER = os.environ.get("PI_USER", "epitech")
PI_IP = os.environ.get("PI_IP", "10.105.174.149")
PI_STREAM_PORT = int(os.environ.get("PI_STREAM_PORT", "8888"))

# Stream state
_stream_cap = None


# --- Pi Camera ---

def _ensure_pi_stream():
    """Lance le stream Pi si pas deja actif, retourne le VideoCapture."""
    global _stream_cap
    if _stream_cap is not None and _stream_cap.isOpened():
        return _stream_cap

    pi = f"{PI_USER}@{PI_IP}"

    # Kill ancien stream
    subprocess.run(["ssh", pi, "pkill -f rpicam-vid"],
                   capture_output=True, timeout=5)
    time.sleep(0.5)

    # Lancer le stream
    ssh_cmd = (
        f"nohup rpicam-vid -t 0 --codec mjpeg --width 1280 --height 960 "
        f"--framerate 15 --inline -l -o tcp://0.0.0.0:{PI_STREAM_PORT} --nopreview "
        f"> /tmp/stream.log 2>&1 & disown"
    )
    subprocess.Popen(["ssh", pi, ssh_cmd],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)

    stream_url = f"tcp://{PI_IP}:{PI_STREAM_PORT}"
    _stream_cap = cv2.VideoCapture(stream_url)

    if not _stream_cap.isOpened():
        _stream_cap = None
        raise RuntimeError(f"Impossible de se connecter au stream Pi: {stream_url}")

    # Vider le buffer (prendre la frame la plus recente)
    for _ in range(5):
        _stream_cap.read()

    return _stream_cap


def _capture_frame():
    """Capture une frame depuis le Pi et la sauvegarde en fichier temp."""
    cap = _ensure_pi_stream()

    # Vider le buffer pour avoir la frame la plus recente
    for _ in range(3):
        cap.read()

    ret, frame = cap.read()
    if not ret:
        # Reconnexion
        global _stream_cap
        _stream_cap = None
        cap = _ensure_pi_stream()
        for _ in range(3):
            cap.read()
        ret, frame = cap.read()
        if not ret:
            raise RuntimeError("Echec capture frame depuis le Pi")

    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    cv2.imwrite(tmp.name, frame)
    tmp.close()
    return tmp.name


def _process_captured_frame():
    """Capture une frame depuis le Pi et la passe dans la pipeline iris."""
    image_path = _capture_frame()
    try:
        template, iris_hash = process_image(image_path)
        return template, iris_hash
    finally:
        os.unlink(image_path)


# --- Database ---

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            address TEXT PRIMARY KEY,
            wallet_name TEXT NOT NULL DEFAULT '',
            iris_codes BLOB NOT NULL,
            mask_codes BLOB NOT NULL,
            iris_code_version TEXT,
            eye_side TEXT DEFAULT 'left',
            balance REAL NOT NULL DEFAULT 0.0,
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_account(address, wallet_name, template, eye_side="left"):
    iris_codes_bytes = _serialize_codes(template.iris_codes)
    mask_codes_bytes = _serialize_codes(template.mask_codes)
    version = getattr(template, 'iris_code_version', None)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO accounts (address, wallet_name, iris_codes, mask_codes, iris_code_version, eye_side, balance, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (address, wallet_name, iris_codes_bytes, mask_codes_bytes, version, eye_side, 0.0, time.time())
    )
    conn.commit()
    conn.close()


def get_account_info(address):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT address, wallet_name, balance, created_at FROM accounts WHERE address = ?",
        (address,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "walletAddress": row[0],
        "walletName": row[1],
        "balance": row[2],
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(row[3])),
    }


def load_all_accounts():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT address, iris_codes, mask_codes, iris_code_version, eye_side, created_at FROM accounts"
    ).fetchall()
    conn.close()

    accounts = []
    for address, iris_codes_bytes, mask_codes_bytes, version, eye_side, created_at in rows:
        template = _deserialize_template(iris_codes_bytes, mask_codes_bytes, version)
        accounts.append({
            "address": address,
            "template": template,
            "eye_side": eye_side,
            "created_at": created_at,
        })
    return accounts


def delete_account(address):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("DELETE FROM accounts WHERE address = ?", (address,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def _serialize_codes(codes):
    parts = []
    for arr in codes:
        parts.append({
            "shape": list(arr.shape),
            "dtype": str(arr.dtype),
            "data": arr.tobytes().hex(),
        })
    return json.dumps(parts).encode()


def _deserialize_codes(raw_bytes):
    parts = json.loads(raw_bytes.decode())
    codes = []
    for p in parts:
        arr = np.frombuffer(bytes.fromhex(p["data"]), dtype=np.dtype(p["dtype"]))
        arr = arr.reshape(p["shape"])
        codes.append(arr)
    return codes


def _deserialize_template(iris_codes_bytes, mask_codes_bytes, version):
    import iris as iris_module
    iris_codes = _deserialize_codes(iris_codes_bytes)
    mask_codes = _deserialize_codes(mask_codes_bytes)
    return iris_module.IrisTemplate(
        iris_codes=iris_codes,
        mask_codes=mask_codes,
        iris_code_version=version,
    )


def _generate_address():
    return "0x" + hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:40]


def _find_match(template):
    accounts = load_all_accounts()
    matcher = get_matcher()

    best_dist = float("inf")
    best_account = None

    for acc in accounts:
        try:
            dist = matcher.run(template, acc["template"])
            if dist < best_dist:
                best_dist = dist
                best_account = acc
        except Exception:
            continue

    if best_dist < MATCH_THRESHOLD:
        return best_account, best_dist

    return None, None


# ======================================================================
#  API pour l'extension (prefix /api)
# ======================================================================

@app.route("/api/scan", methods=["POST"])
def api_scan():
    """Capture une photo depuis le Pi et identifie l'iris.

    Pas de body requis — le backend pilote la camera.

    Retourne:
        - {found: true, wallet: WalletData} si iris reconnu
        - {found: false, irisHash: "..."} si iris inconnu
    """
    try:
        template, iris_hash = _process_captured_frame()
        match, dist = _find_match(template)

        if match is not None:
            wallet_info = get_account_info(match["address"])
            wallet_info["irisHash"] = iris_hash
            return jsonify({
                "found": True,
                "wallet": wallet_info,
                "distance": round(dist, 4),
            })

        return jsonify({
            "found": False,
            "irisHash": iris_hash,
        })

    except RuntimeError as e:
        return jsonify({"error": f"Pipeline echoue: {e}"}), 422
    except Exception as e:
        return jsonify({"error": f"Erreur: {e}"}), 500


@app.route("/api/register", methods=["POST"])
def api_register():
    """Enregistre un nouvel iris avec un nom de wallet.

    Body JSON: { irisHash: string, walletName: string }
    Le irisHash vient du /api/scan precedent. On re-capture pour avoir
    le template frais (le hash sert juste de confirmation).

    Retourne:
        - {found: true, wallet: WalletData}
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Body JSON requis"}), 400

    wallet_name = data.get("walletName", "").strip()
    if not wallet_name:
        return jsonify({"error": "walletName requis"}), 400

    try:
        # Re-capture pour avoir le template
        template, iris_hash = _process_captured_frame()

        # Verifier que cet iris n'existe pas deja
        match, dist = _find_match(template)
        if match is not None:
            wallet_info = get_account_info(match["address"])
            wallet_info["irisHash"] = iris_hash
            return jsonify({
                "found": True,
                "wallet": wallet_info,
                "alreadyExists": True,
                "distance": round(dist, 4),
            })

        # Creer le compte
        address = _generate_address()
        save_account(address, wallet_name, template)

        wallet_info = get_account_info(address)
        wallet_info["irisHash"] = iris_hash

        return jsonify({
            "found": True,
            "wallet": wallet_info,
        }), 201

    except RuntimeError as e:
        return jsonify({"error": f"Pipeline echoue: {e}"}), 422
    except Exception as e:
        return jsonify({"error": f"Erreur: {e}"}), 500


@app.route("/api/auth", methods=["POST"])
def api_auth():
    """Alias pour /api/scan — compatibilite avec l'extension existante."""
    return api_scan()


# ======================================================================
#  API directe (upload image)
# ======================================================================

@app.route("/enroll", methods=["POST"])
def enroll():
    if "image" not in request.files:
        return jsonify({"error": "Champ 'image' requis"}), 400

    file = request.files["image"]
    eye_side = request.form.get("eye_side", "left")
    wallet_name = request.form.get("wallet_name", "Wallet")

    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    file.save(tmp.name)
    tmp.close()

    try:
        template, iris_hash = process_image(tmp.name, eye_side)
        match, dist = _find_match(template)

        if match is not None:
            return jsonify({
                "address": match["address"],
                "hash": iris_hash,
                "new": False,
                "distance": round(dist, 4),
            }), 200

        address = _generate_address()
        save_account(address, wallet_name, template, eye_side)

        return jsonify({
            "address": address,
            "hash": iris_hash,
            "new": True,
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.unlink(tmp.name)


@app.route("/identify", methods=["POST"])
def identify():
    if "image" not in request.files:
        return jsonify({"error": "Champ 'image' requis"}), 400

    file = request.files["image"]
    eye_side = request.form.get("eye_side", "left")

    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    file.save(tmp.name)
    tmp.close()

    try:
        template, iris_hash = process_image(tmp.name, eye_side)
        match, dist = _find_match(template)

        if match is not None:
            return jsonify({
                "address": match["address"],
                "hash": iris_hash,
                "distance": round(dist, 4),
                "known": True,
            }), 200

        return jsonify({"hash": iris_hash, "known": False}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.unlink(tmp.name)


@app.route("/accounts", methods=["GET"])
@app.route("/api/accounts", methods=["GET"])
def list_accounts():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT address, wallet_name, balance, created_at FROM accounts"
    ).fetchall()
    conn.close()

    return jsonify({
        "count": len(rows),
        "accounts": [
            {
                "address": addr,
                "walletName": name,
                "balance": bal,
                "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
            }
            for addr, name, bal, ts in rows
        ],
    })


@app.route("/accounts/<address>", methods=["DELETE"])
def remove_account(address):
    if delete_account(address):
        return jsonify({"message": "Compte supprime", "address": address}), 200
    return jsonify({"error": "Compte non trouve"}), 404


@app.route("/health", methods=["GET"])
def health():
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    conn.close()

    stream_ok = _stream_cap is not None and _stream_cap.isOpened()
    return jsonify({
        "status": "ok",
        "accounts": count,
        "threshold": MATCH_THRESHOLD,
        "pi_stream": "connected" if stream_ok else "disconnected",
        "pi_ip": PI_IP,
    })


# --- Main ---

if __name__ == "__main__":
    print("=" * 60)
    print("  IrisGate Backend")
    print("=" * 60)
    print()
    print("  Chargement du modele iris...")
    get_pipeline()
    print("  Modele charge !")
    print()
    init_db()
    print(f"  DB: {DB_PATH}")
    print(f"  Pi: {PI_USER}@{PI_IP}:{PI_STREAM_PORT}")
    print(f"  Seuil match: {MATCH_THRESHOLD}")
    print()
    print("  Endpoints extension:")
    print("    POST /api/scan      — scanner iris via Pi")
    print("    POST /api/register  — creer un compte")
    print("    GET  /api/accounts  — lister les comptes")
    print()
    print("  Endpoints directs:")
    print("    POST /enroll    — inscrire (upload image)")
    print("    POST /identify  — identifier (upload image)")
    print("    GET  /health    — status")
    print()
    app.run(host="0.0.0.0", port=5000, debug=False)
