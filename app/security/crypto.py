import base64
import binascii
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings

NONCE_SIZE = 12
KEY_SIZE = 32
TAG_SIZE = 16


class DecryptionError(ValueError):
    pass


def _load_key() -> bytes:
    raw = get_settings().field_encryption_key
    if not raw:
        raise RuntimeError(
            "FIELD_ENCRYPTION_KEY is not set. Generate one with:\n"
            '  python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"\n'
            "and put it in your .env file."
        )
    try:
        key = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RuntimeError("FIELD_ENCRYPTION_KEY is not valid base64") from exc
    if len(key) != KEY_SIZE:
        raise RuntimeError(
            f"FIELD_ENCRYPTION_KEY must decode to {KEY_SIZE} bytes (AES-256), got {len(key)}"
        )
    return key


def encrypt_field(plaintext: str, aad: bytes | None = None) -> str:
    aesgcm = AESGCM(_load_key())
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt_field(token: str, aad: bytes | None = None) -> str:
    try:
        blob = base64.b64decode(token, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise DecryptionError("Encrypted value is not valid base64") from exc

    if len(blob) < NONCE_SIZE + TAG_SIZE:
        raise DecryptionError("Encrypted value is too short")

    nonce, ciphertext = blob[:NONCE_SIZE], blob[NONCE_SIZE:]
    try:
        plaintext = AESGCM(_load_key()).decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:
        raise DecryptionError("Integrity check failed: value was tampered with or the key is wrong") from exc
    return plaintext.decode("utf-8")
