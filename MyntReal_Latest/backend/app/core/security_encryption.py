"""
AES-256-GCM Credential Encryption Module (Release 1A Security Layer)
Encrypts sensitive API tokens and credentials stored in PostgreSQL tables.
Format: gcm:v1:<base64_nonce>:<base64_ciphertext>:<base64_tag>
"""

import os
import base64
import logging
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

PREFIX = "gcm:v1:"


class UnencryptedCredentialError(Exception):
    """Raised when an unencrypted credential is encountered in strict mode."""
    pass


def _get_master_key() -> bytes:
    """
    Retrieve 256-bit (32-byte) master encryption key.
    Loads from MYNTOS_ENCRYPTION_MASTER_KEY environment variable.
    If missing or invalid length, generates a deterministic key for fallback/dev.
    """
    raw_key = os.environ.get("MYNTOS_ENCRYPTION_MASTER_KEY", "")
    if raw_key:
        try:
            key_bytes = base64.b64decode(raw_key)
            if len(key_bytes) == 32:
                return key_bytes
            elif len(raw_key.encode('utf-8')) == 32:
                return raw_key.encode('utf-8')
        except Exception:
            pass
        if len(raw_key.encode('utf-8')) >= 32:
            return raw_key.encode('utf-8')[:32]

    # Fixed fallback key for local dev / testing if env var not set
    fallback_seed = "myntos_secret_master_key_2026_prod_v1_32b!"
    return fallback_seed.encode('utf-8')[:32]


def encrypt_credential(plaintext: str) -> str:
    """
    Encrypt plaintext string using AES-256-GCM.
    Returns: 'gcm:v1:<nonce_b64>:<ciphertext_b64>:<tag_b64>'
    """
    if not plaintext:
        return ""
    if plaintext.startswith(PREFIX):
        return plaintext  # Already encrypted

    try:
        key = _get_master_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # 96-bit random nonce
        
        raw_encrypted = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        ciphertext = raw_encrypted[:-16]
        tag = raw_encrypted[-16:]

        nonce_b64 = base64.b64encode(nonce).decode('utf-8')
        cipher_b64 = base64.b64encode(ciphertext).decode('utf-8')
        tag_b64 = base64.b64encode(tag).decode('utf-8')

        return f"{PREFIX}{nonce_b64}:{cipher_b64}:{tag_b64}"
    except Exception as e:
        logger.error(f"[ENCRYPT-ERROR] Failed to encrypt credential: {e}")
        raise RuntimeError(f"Encryption failed: {e}")


def decrypt_credential(encrypted_str: str, strict_mode: bool = False) -> str:
    """
    Decrypt string formatted as 'gcm:v1:<nonce_b64>:<ciphertext_b64>:<tag_b64>'.
    If not starting with 'gcm:v1:':
      - If strict_mode=True: raises UnencryptedCredentialError
      - If strict_mode=False: returns plaintext string (legacy fallback)
    """
    if not encrypted_str:
        return ""
    
    if not encrypted_str.startswith(PREFIX):
        if strict_mode:
            raise UnencryptedCredentialError("Encountered unencrypted credential in strict mode")
        return encrypted_str  # Legacy plaintext fallback for non-strict reads

    try:
        payload = encrypted_str[len(PREFIX):]
        parts = payload.split(":")
        if len(parts) != 3:
            raise ValueError("Malformed encrypted credential format")

        nonce = base64.b64decode(parts[0])
        ciphertext = base64.b64decode(parts[1])
        tag = base64.b64decode(parts[2])

        key = _get_master_key()
        aesgcm = AESGCM(key)
        
        raw_combined = ciphertext + tag
        decrypted_bytes = aesgcm.decrypt(nonce, raw_combined, None)
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"[DECRYPT-ERROR] Decryption failed: {e}")
        if strict_mode:
            raise RuntimeError(f"Decryption failed in strict mode: {e}")
        return encrypted_str


def decrypt_credential_safe(encrypted_str: str) -> str:
    """Safe wrapper: decrypts string or returns fallback without crashing application."""
    try:
        from app.core.config import settings
        strict = getattr(settings, 'STRICT_ENCRYPTED_CREDS_ONLY', False)
        return decrypt_credential(encrypted_str, strict_mode=strict)
    except UnencryptedCredentialError:
        logger.error("[SECURITY-ALERT] Plaintext credential detected in strict mode!")
        return ""
    except Exception:
        return encrypted_str
