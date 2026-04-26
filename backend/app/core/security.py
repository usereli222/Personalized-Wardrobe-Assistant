"""
Token + password helpers — STUB.

Mentees: replace these with real JWT (e.g. python-jose) and bcrypt
(passlib[bcrypt]). The signatures here are the contract the rest of the app
relies on; keep them stable so the routers don't have to change.
"""

from __future__ import annotations


def hash_password(plain: str) -> str:
    # TODO(mentee): replace with bcrypt — `passlib.hash.bcrypt.hash(plain)`.
    return f"plain::{plain}"


def verify_password(plain: str, hashed: str) -> bool:
    # TODO(mentee): replace with `passlib.hash.bcrypt.verify(plain, hashed)`.
    return hashed == f"plain::{plain}"


def create_token(username: str) -> str:
    # TODO(mentee): issue a real JWT signed with a server-side secret,
    # carrying { "sub": username, "exp": ... }.
    return username


def decode_token(token: str) -> str | None:
    # TODO(mentee): verify signature + expiry, return the username (sub) or None.
    return token or None
