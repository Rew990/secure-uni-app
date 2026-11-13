"""Field-level encryption with AES-256-GCM (owner: Encryption & TLS).

Used for `students.national_id_enc` and `users.mfa_secret_enc`.

TODO(encryption):
  - load the 32-byte key from settings.field_encryption_key (base64)
  - encrypt_field: random 12-byte nonce + AESGCM(key).encrypt(nonce, data, aad)
    and return base64(nonce + ciphertext)
  - decrypt_field: reverse it; raise on tampering (InvalidTag)
  - unit tests in tests/test_crypto.py
"""


def encrypt_field(plaintext: str, aad: bytes | None = None) -> str:
    raise NotImplementedError("Encryption: encrypt_field")


def decrypt_field(token: str, aad: bytes | None = None) -> str:
    raise NotImplementedError("Encryption: decrypt_field")
