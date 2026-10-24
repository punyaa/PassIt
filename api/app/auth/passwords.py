"""Password hashing with argon2id. Plaintext passwords are never logged or stored."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()

# Verified against when the email is unknown, so a miss costs the same as a wrong password
# and response time does not reveal which emails are registered.
_UNKNOWN_USER_HASH = _hasher.hash("passit-unknown-user-placeholder")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, stored_hash: str | None) -> bool:
    """False for a wrong password and for hashes that are not argon2 (e.g. seed accounts)."""
    try:
        _hasher.verify(stored_hash or _UNKNOWN_USER_HASH, password)
    except (VerificationError, InvalidHashError):
        return False
    return stored_hash is not None
