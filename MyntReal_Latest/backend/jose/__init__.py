"""
jose compatibility shim — wraps PyJWT so that all existing `from jose import jwt, JWTError`
style imports continue to work without modification.

python-jose was replaced by PyJWT (already a direct dependency) because the ecdsa package
that python-jose pulls in has no available patched version for GHSA-wj6h-64fc-37mp.
"""

import jwt as _pyjwt

from jwt.exceptions import (
    PyJWTError as JWTError,
    ExpiredSignatureError,
    DecodeError,
    InvalidTokenError,
    InvalidAlgorithmError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidIssuedAtError,
    ImmatureSignatureError,
    InvalidSignatureError,
    MissingRequiredClaimError,
)

jwt = _pyjwt

from .exceptions import ExpiredSignatureError  # noqa: F811 — re-export via submodule too

__all__ = [
    "jwt",
    "JWTError",
    "ExpiredSignatureError",
    "DecodeError",
    "InvalidTokenError",
]
