"""Utilitaires de chiffrement AES-256-GCM pour les templates iris."""

import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from config import AES_KEY_SIZE, AES_NONCE_SIZE


def generate_key() -> bytes:
    """Genere une cle AES-256 aleatoire."""
    return AESGCM.generate_key(bit_length=AES_KEY_SIZE * 8)


def encrypt_template(template: bytes, key: bytes) -> dict:
    """Chiffre un template iris avec AES-256-GCM.

    Retourne un dict avec le nonce et le ciphertext en base64.
    """
    nonce = os.urandom(AES_NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, template, None)

    return {
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
    }


def decrypt_template(encrypted: dict, key: bytes) -> bytes:
    """Dechiffre un template iris."""
    nonce = base64.b64decode(encrypted["nonce"])
    ciphertext = base64.b64decode(encrypted["ciphertext"])
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)
