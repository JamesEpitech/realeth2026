"""Stream live depuis le Raspberry Pi + pipeline iris-recognition + backend IrisGate.

Affiche le flux en direct depuis la camera du Pi.
  ESPACE = capturer + identifier (cherche le compte associe)
  E      = capturer + enregistrer (cree un nouveau compte)
  P      = sauvegarder photo brute
  R      = reprendre apres freeze
  Q/ESC  = quitter

Usage:
  python remote_live.py                    # mode local (pipeline locale)
  python remote_live.py --backend          # envoie au backend IrisGate
  python remote_live.py --backend-url http://host:port  # backend custom
"""

import sys
import os
import time
import subprocess
import tempfile

import cv2
import numpy as np

# Ajouter le dossier courant au path pour importer iris_recognition
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iris_recognition import process_image, compare, get_pipeline, template_to_hash

# --- Config Pi ---
PI_USER = os.environ.get("PI_USER", "epitech")
PI_IP = os.environ.get("PI_IP", "10.105.174.149")
PI_STREAM_PORT = int(os.environ.get("PI_STREAM_PORT", "8888"))

# --- Config Backend ---
BACKEND_URL = os.environ.get("IRISGATE_URL", "http://localhost:5000")

# --- Couleurs ---
GREEN = (0, 255, 0)
RED = (0, 0, 255)
YELLOW = (0, 255, 255)
WHITE = (255, 255, 255)
GRAY = (180, 180, 180)
DARK_BG = (30, 30, 30)
CYAN = (255, 255, 0)


def draw_text(frame, text, pos, color=WHITE, scale=0.5, thickness=1):
    font = cv2.FONT_HERSHEY_SIMPLEX
    (w, h), _ = cv2.getTextSize(text, font, scale, thickness)
    x, y = pos
    cv2.rectangle(frame, (x - 2, y - h - 4), (x + w + 2, y + 4), DARK_BG, -1)
    cv2.putText(frame, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)


def start_pi_stream():
    pi = f"{PI_USER}@{PI_IP}"
    subprocess.run(["ssh", pi, "pkill -f rpicam-vid"],
                   capture_output=True, timeout=5)
    time.sleep(0.5)
    ssh_cmd = (
        f"nohup rpicam-vid -t 0 --codec mjpeg --width 1280 --height 960 "
        f"--framerate 15 --inline -l -o tcp://0.0.0.0:{PI_STREAM_PORT} --nopreview "
        f"> /tmp/stream.log 2>&1 & disown"
    )
    subprocess.Popen(["ssh", pi, ssh_cmd],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def stop_pi_stream():
    pi = f"{PI_USER}@{PI_IP}"
    subprocess.run(["ssh", pi, "pkill -f rpicam-vid"],
                   capture_output=True, timeout=5)


def send_to_backend(image_path, endpoint):
    """Envoie une image au backend IrisGate. Retourne le JSON de reponse."""
    import requests
    url = f"{BACKEND_URL}/{endpoint}"
    with open(image_path, "rb") as f:
        resp = requests.post(url, files={"image": f})
    resp.raise_for_status()
    return resp.json()


def make_result_screen(frame, success, lines):
    """Cree un ecran de resultat (vert=succes, rouge=echec)."""
    result = frame.copy()
    overlay = result.copy()
    bg_color = (0, 80, 0) if success else (0, 0, 80)
    cv2.rectangle(overlay, (0, 0), (result.shape[1], result.shape[0]), bg_color, -1)
    cv2.addWeighted(overlay, 0.3, result, 0.7, 0, result)

    font = cv2.FONT_HERSHEY_SIMPLEX
    cx = result.shape[1] // 2
    cy = result.shape[0] // 2

    for text, dy, scale, color in lines:
        (tw, _), _ = cv2.getTextSize(text, font, scale, 2)
        cv2.putText(result, text, (cx - tw // 2, cy + dy),
                    font, scale, color, 2, cv2.LINE_AA)

    if success:
        cv2.circle(result, (cx, cy - 140), 50, GREEN, 4)
        cv2.line(result, (cx - 25, cy - 140), (cx - 5, cy - 120), GREEN, 4)
        cv2.line(result, (cx - 5, cy - 120), (cx + 30, cy - 165), GREEN, 4)

    return result


def do_scan(frame, mode, use_backend):
    """Execute un scan (enroll ou identify). Retourne (result_display, info_dict)."""
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    cv2.imwrite(tmp.name, frame)
    tmp.close()

    try:
        if use_backend:
            data = send_to_backend(tmp.name, mode)
            address = data.get("address", "N/A")
            iris_hash = data.get("hash", "???")
            is_new = data.get("new", False)
            is_known = data.get("known", False)
            distance = data.get("distance")
            error = data.get("error")

            if error:
                raise RuntimeError(error)

            if mode == "enroll":
                if is_new:
                    lines = [
                        ("COMPTE CREE", -60, 1.0, GREEN),
                        (f"Adresse: {address[:22]}...", -10, 0.6, WHITE),
                        (f"Hash: {iris_hash}", 30, 0.6, CYAN),
                        ("Vous pouvez retirer votre oeil.", 70, 0.5, GREEN),
                        ("R = reprendre", 110, 0.5, GRAY),
                    ]
                    print(f"  [NOUVEAU] Adresse: {address}")
                    print(f"  [NOUVEAU] Hash: {iris_hash}")
                else:
                    lines = [
                        ("IRIS DEJA ENREGISTRE", -60, 0.9, YELLOW),
                        (f"Adresse: {address[:22]}...", -10, 0.6, WHITE),
                        (f"Distance: {distance:.4f}", 30, 0.6, CYAN),
                        ("R = reprendre", 70, 0.5, GRAY),
                    ]
                    print(f"  [EXISTANT] Adresse: {address} (dist={distance:.4f})")
                return make_result_screen(frame, True, lines), data

            else:  # identify
                if is_known:
                    lines = [
                        ("IRIS RECONNU", -60, 1.0, GREEN),
                        (f"Adresse: {address[:22]}...", -10, 0.6, WHITE),
                        (f"Distance: {distance:.4f}", 30, 0.6, CYAN),
                        ("Vous pouvez retirer votre oeil.", 70, 0.5, GREEN),
                        ("R = reprendre", 110, 0.5, GRAY),
                    ]
                    print(f"  [RECONNU] Adresse: {address} (dist={distance:.4f})")
                else:
                    lines = [
                        ("IRIS INCONNU", -40, 1.0, YELLOW),
                        ("Aucun compte associe", 10, 0.6, WHITE),
                        ("Appuyez E pour creer un compte", 50, 0.5, CYAN),
                        ("R = reprendre", 90, 0.5, GRAY),
                    ]
                    print(f"  [INCONNU] Pas de compte associe")
                return make_result_screen(frame, is_known, lines), data

        else:
            # Mode local (sans backend)
            template, iris_hash = process_image(tmp.name)
            print(f"  [OK] Hash: {iris_hash}")

            lines = [
                ("SCAN REUSSI", -60, 1.2, GREEN),
                (f"Hash: {iris_hash}", 0, 0.8, WHITE),
                ("Vous pouvez retirer votre oeil.", 50, 0.6, GREEN),
                ("R = reprendre", 90, 0.5, GRAY),
            ]
            return make_result_screen(frame, True, lines), {
                "hash": iris_hash, "template": template
            }

    except Exception as e:
        print(f"  [ERREUR] {e}")
        lines = [
            ("SCAN ECHOUE", -20, 1.0, RED),
            (str(e)[:60], 30, 0.5, WHITE),
            ("R = reprendre", 70, 0.5, GRAY),
        ]
        return make_result_screen(frame, False, lines), {"error": str(e)}

    finally:
        os.unlink(tmp.name)


def main():
    # --- Parse args ---
    use_backend = "--backend" in sys.argv or "--backend-url" in sys.argv
    if "--backend-url" in sys.argv:
        idx = sys.argv.index("--backend-url")
        global BACKEND_URL
        BACKEND_URL = sys.argv[idx + 1]

    print("=" * 60)
    print("  IRISWALLET — Remote Live + Iris Recognition")
    print("=" * 60)
    print()
    print(f"  Pi : {PI_USER}@{PI_IP}")
    if use_backend:
        print(f"  Backend : {BACKEND_URL}")
    else:
        print("  Mode : local (pas de backend)")
    print()

    if not use_backend:
        print("  Chargement du modele iris...")
        get_pipeline()
        print("  Modele charge !")
        print()

    # Lancer le stream
    print("  Demarrage du stream sur le Pi...")
    start_pi_stream()
    stream_url = f"tcp://{PI_IP}:{PI_STREAM_PORT}"
    print(f"  Stream : {stream_url}")

    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        print(f"[ERREUR] Impossible de se connecter au stream")
        stop_pi_stream()
        return

    print("  Connecte !")
    print()
    if use_backend:
        print("  Commandes :")
        print("    ESPACE = identifier (chercher le compte)")
        print("    E      = enregistrer (creer un compte)")
        print("    P      = sauvegarder photo brute")
        print("    R      = reprendre apres freeze")
        print("    Q/ESC  = quitter")
    else:
        print("  Commandes :")
        print("    ESPACE = scanner (pipeline locale)")
        print("    P      = sauvegarder photo brute")
        print("    R      = reprendre apres freeze")
        print("    Q/ESC  = quitter")
    print()

    cv2.namedWindow("IrisWallet — Remote Live", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("IrisWallet — Remote Live", 1280, 720)

    scan_count = 0
    photo_count = 0
    last_hash = None
    last_address = None

    frozen = False
    frozen_display = None

    while True:
        if frozen:
            cv2.imshow("IrisWallet — Remote Live", frozen_display)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):
                break
            elif key == ord('r'):
                frozen = False
                frozen_display = None
                print("[RESUME] Camera live")
            continue

        ret, frame = cap.read()
        if not ret:
            blank = np.zeros((720, 1280, 3), dtype=np.uint8)
            draw_text(blank, "Connexion perdue... reconnexion...", (400, 360), RED, 0.8)
            cv2.imshow("IrisWallet — Remote Live", blank)
            key = cv2.waitKey(500) & 0xFF
            if key in (ord('q'), 27):
                break
            cap.release()
            cap = cv2.VideoCapture(stream_url)
            continue

        display = frame.copy()

        # --- Indicateurs ---
        if use_backend:
            draw_text(display, "ESPACE=Identifier | E=Enregistrer",
                      (display.shape[1] // 2 - 180, 30), GREEN, 0.6)
        else:
            draw_text(display, "ESPACE pour scanner",
                      (display.shape[1] // 2 - 100, 30), GREEN, 0.7)

        if last_address:
            draw_text(display, f"Compte: {last_address[:22]}...", (10, 30), CYAN, 0.45)
        elif last_hash:
            draw_text(display, f"Hash: {last_hash}", (10, 30), YELLOW, 0.45)

        # Barre du bas
        bar_y = display.shape[0] - 35
        cv2.rectangle(display, (0, bar_y), (display.shape[1], display.shape[0]), DARK_BG, -1)
        if use_backend:
            controls = "SPACE=Identify | E=Enroll | P=Photo | R=Resume | Q=Quit"
        else:
            controls = "SPACE=Scan | P=Photo | R=Resume | Q=Quit"
        draw_text(display, controls, (10, display.shape[0] - 12), GRAY, 0.4)
        draw_text(display, f"Scans: {scan_count}",
                  (display.shape[1] - 100, display.shape[0] - 12), YELLOW, 0.45)

        cv2.imshow("IrisWallet — Remote Live", display)
        key = cv2.waitKey(1) & 0xFF

        if key in (ord('q'), 27):
            break

        elif key == ord('p'):
            photo_count += 1
            filename = f"photo_{time.strftime('%H%M%S')}_{photo_count}.jpg"
            cv2.imwrite(filename, frame)
            print(f"[PHOTO] {filename}")

        elif key == ord(' '):
            scan_count += 1
            frozen = True

            scan_disp = display.copy()
            draw_text(scan_disp, "IDENTIFICATION EN COURS...",
                      (display.shape[1] // 2 - 150, display.shape[0] // 2), YELLOW, 0.9)
            frozen_display = scan_disp
            cv2.imshow("IrisWallet — Remote Live", frozen_display)
            cv2.waitKey(1)

            mode = "identify" if use_backend else "local"
            print(f"\n>>> SCAN #{scan_count} — {mode}...")
            frozen_display, data = do_scan(frame, mode, use_backend)

            last_hash = data.get("hash")
            last_address = data.get("address")

        elif key == ord('e') and use_backend:
            scan_count += 1
            frozen = True

            scan_disp = display.copy()
            draw_text(scan_disp, "ENREGISTREMENT EN COURS...",
                      (display.shape[1] // 2 - 150, display.shape[0] // 2), YELLOW, 0.9)
            frozen_display = scan_disp
            cv2.imshow("IrisWallet — Remote Live", frozen_display)
            cv2.waitKey(1)

            print(f"\n>>> ENROLL #{scan_count}...")
            frozen_display, data = do_scan(frame, "enroll", use_backend)

            last_hash = data.get("hash")
            last_address = data.get("address")

    cap.release()
    cv2.destroyAllWindows()
    stop_pi_stream()
    print("\nStream arrete. Bye!")


if __name__ == "__main__":
    main()
