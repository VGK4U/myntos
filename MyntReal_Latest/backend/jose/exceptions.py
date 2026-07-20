"""
jose.exceptions compatibility shim for PyJWT.
Provides the same exception names that python-jose exported.
"""

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

__all__ = [
    "JWTError",
    "ExpiredSignatureError",
    "DecodeError",
    "InvalidTokenError",
]
