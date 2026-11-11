"""Authenticated local encryption and stable pseudonymous developer IDs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from collections.abc import Mapping
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

FORMAT_VERSION = 1
KDF_ITERATIONS = 600_000


def _seed_bytes(seed: str) -> bytes:
    if not seed or not seed.strip():
        raise ValueError("seed must not be empty")
    return seed.encode("utf-8")


def developer_id(name: str, email: str, seed: str) -> str:
    """Return a stable pseudonymous ID scoped to this seed."""
    normalized = f"{name.strip().casefold()}\0{email.strip().casefold()}".encode()
    id_key = hmac.new(_seed_bytes(seed), b"codescan-developer-id-v1", hashlib.sha256).digest()
    digest = hmac.new(id_key, normalized, hashlib.sha256).hexdigest()[:16].upper()
    return f"DEV-{digest}"


def _fernet_key(seed: str, salt: bytes, iterations: int) -> bytes:
    key = hashlib.pbkdf2_hmac("sha256", _seed_bytes(seed), salt, iterations, dklen=32)
    return base64.urlsafe_b64encode(key)


def encrypt_identity_map(identities: Mapping[str, Any], seed: str) -> str:
    """Encrypt the identity map in a versioned envelope using Fernet authentication."""
    salt = os.urandom(16)
    fernet = Fernet(_fernet_key(seed, salt, KDF_ITERATIONS))
    plaintext = json.dumps(identities, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    token = fernet.encrypt(plaintext.encode("utf-8"))
    envelope = {
        "format_version": FORMAT_VERSION,
        "kdf": "PBKDF2-HMAC-SHA256",
        "iterations": KDF_ITERATIONS,
        "salt": base64.urlsafe_b64encode(salt).decode("ascii"),
        "cipher": "Fernet",
        "ciphertext": token.decode("ascii"),
    }
    return json.dumps(envelope, indent=2, sort_keys=True) + "\n"


def decrypt_identity_map(envelope_text: str, seed: str) -> dict[str, Any]:
    """Decrypt and validate a CodeScan encrypted identity envelope."""
    try:
        envelope = json.loads(envelope_text)
        if envelope.get("format_version") != FORMAT_VERSION:
            raise ValueError("unsupported encrypted identity format version")
        if envelope.get("kdf") != "PBKDF2-HMAC-SHA256" or envelope.get("cipher") != "Fernet":
            raise ValueError("unsupported encrypted identity algorithms")
        iterations = int(envelope["iterations"])
        if not 100_000 <= iterations <= 2_000_000:
            raise ValueError("invalid key derivation work factor")
        salt = base64.urlsafe_b64decode(envelope["salt"])
        token = envelope["ciphertext"].encode("ascii")
        plaintext = Fernet(_fernet_key(seed, salt, iterations)).decrypt(token)
        payload = json.loads(plaintext.decode("utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("decrypted identity map has an invalid structure")
        return payload
    except InvalidToken as exc:
        raise ValueError("unable to decrypt identity map; check the seed and input file") from exc
    except (KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith(
            ("unsupported", "invalid", "decrypted", "unable")
        ):
            raise
        raise ValueError("invalid encrypted identity file") from exc
