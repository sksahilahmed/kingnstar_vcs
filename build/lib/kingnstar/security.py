"""
Security module for Kingnstar VCS
Handles password hashing and validation
"""

import hashlib
from kingnstar.constants import MASTER_PASSWORD


def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash"""
    return hash_password(password) == stored_hash


def is_master_password(password: str) -> bool:
    """Check if password is the master password"""
    return password == MASTER_PASSWORD
