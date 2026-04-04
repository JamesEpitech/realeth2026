"""
Iris Recognition System
Utilise open-iris (Worldcoin) pour le pipeline complet.
"""

import cv2
import iris
import numpy as np
import hashlib
import sys
import os


# ─── Pipeline & Matcher (singletons) ─────────────────────────────────────────

_pipeline = None
_matcher = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = iris.IRISPipeline()
    return _pipeline


def get_matcher():
    global _matcher
    if _matcher is None:
        _matcher = iris.HammingDistanceMatcher()
    return _matcher


# ─── Fonctions utilitaires ───────────────────────────────────────────────────

def template_to_hash(template):
    """Génère un hash hex court à partir d'un IrisTemplate."""
    data = np.concatenate([c.flatten() for c in template.iris_codes])
    return hashlib.sha256(np.packbits(data).tobytes()).hexdigest()[:16]


def process_image(image_path, eye_side="left"):
    """
    Pipeline complet : image → (template, hash).
    Raise si l'image ne peut pas être traitée.
    """
    gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise FileNotFoundError(f"Impossible de lire: {image_path}")

    output = get_pipeline()(
        iris.IRImage(img_data=gray, image_id=image_path, eye_side=eye_side)
    )

    if output["error"] is not None:
        raise RuntimeError(f"Erreur pipeline: {output['error']}")

    template = output["iris_template"]
    h = template_to_hash(template)
    return template, h


def compare(template1, template2):
    """Distance de Hamming entre deux templates."""
    return get_matcher().run(template1, template2)


# ─── Base de données d'iris ──────────────────────────────────────────────────

class IrisDB:
    def __init__(self, threshold=0.35):
        self.threshold = threshold
        self.entries = []  # [(template, hash, source_path)]

    def enroll(self, image_path, eye_side="left"):
        """
        Enregistre un iris. Retourne (hash, distance, deja_connu).
        Si l'iris match un existant, retourne le hash existant.
        """
        template, h = process_image(image_path, eye_side)

        for existing_template, existing_hash, _ in self.entries:
            dist = compare(template, existing_template)
            if dist < self.threshold:
                return existing_hash, dist, True

        self.entries.append((template, h, image_path))
        return h, 0.0, False

    def identify(self, image_path, eye_side="left"):
        """
        Identifie un iris. Retourne (hash, distance) du meilleur match,
        ou (nouveau_hash, None) si inconnu.
        """
        template, h = process_image(image_path, eye_side)

        best_dist = float("inf")
        best_hash = None

        for existing_template, existing_hash, _ in self.entries:
            dist = compare(template, existing_template)
            if dist < best_dist:
                best_dist = dist
                best_hash = existing_hash

        if best_dist < self.threshold:
            return best_hash, best_dist
        return h, None


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python iris.py compare <image1> <image2>")
        print("  python iris.py identify <image1> [image2] [image3] ...")
        sys.exit(1)

    command = sys.argv[1]

    if command == "compare":
        if len(sys.argv) != 4:
            print("Usage: python iris.py compare <image1> <image2>")
            sys.exit(1)

        img1, img2 = sys.argv[2], sys.argv[3]
        print("Comparaison de deux iris...")
        t1, h1 = process_image(img1)
        t2, h2 = process_image(img2)
        dist = compare(t1, t2)
        is_match = dist < 0.35

        print(f"  Image 1: hash={h1}")
        print(f"  Image 2: hash={h2}")
        print(f"  Distance de Hamming: {dist:.4f}")
        print(f"  Resultat: {'MEME IRIS' if is_match else 'IRIS DIFFERENTS'}")

    elif command == "identify":
        images = sys.argv[2:]
        db = IrisDB()

        print(f"Identification de {len(images)} image(s)...\n")
        for img_path in images:
            try:
                h, dist, known = db.enroll(img_path)
                name = os.path.basename(img_path)
                if known:
                    print(f"  {name} -> iris:{h} (connu, dist={dist:.4f})")
                else:
                    print(f"  {name} -> iris:{h} (nouveau)")
            except Exception as e:
                print(f"  {os.path.basename(img_path)} -> ERREUR: {e}")

        print(f"\n{len(db.entries)} iris unique(s) detecte(s)")
