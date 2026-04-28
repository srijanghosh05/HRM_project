from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


USER_DB_FILE = Path(__file__).with_name("users.json")
PBKDF2_ITERATIONS = 260_000
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
EMPLOYEE_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{3,20}$")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(normalize_email(email)))


def is_valid_employee_id(employee_id: str) -> bool:
    return bool(EMPLOYEE_ID_PATTERN.match(employee_id.strip()))


def validate_password_strength(password: str) -> list[str]:
    issues: list[str] = []
    if len(password) < 8:
        issues.append("at least 8 characters")
    if not any(character.isupper() for character in password):
        issues.append("one uppercase letter")
    if not any(character.islower() for character in password):
        issues.append("one lowercase letter")
    if not any(character.isdigit() for character in password):
        issues.append("one number")
    return issues


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    salt_text = base64.b64encode(salt).decode("ascii")
    hash_text = base64.b64encode(password_hash).decode("ascii")
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_text}${hash_text}"


def verify_password(password: str, stored_password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_text, expected_hash = stored_password_hash.split("$")
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    salt = base64.b64decode(salt_text.encode("ascii"))
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        int(iterations),
    )
    candidate_text = base64.b64encode(candidate).decode("ascii")
    return hmac.compare_digest(candidate_text, expected_hash)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_users() -> list[dict[str, Any]]:
    return [
        {
            "user_id": str(uuid4()),
            "full_name": "HR Rewards Manager",
            "employee_id": "MGR001",
            "email": "manager@company.com",
            "department": "Human Resources",
            "role": "manager",
            "role_locked": True,
            "admin_created": True,
            "password_hash": hash_password("Manager@123"),
            "created_at": _now_iso(),
        },
        {
            "user_id": str(uuid4()),
            "full_name": "Aarav Sharma",
            "employee_id": "EMP001",
            "email": "aarav.sharma@company.com",
            "department": "Engineering",
            "role": "employee",
            "role_locked": True,
            "admin_created": False,
            "password_hash": hash_password("Employee@123"),
            "created_at": _now_iso(),
        },
    ]


def ensure_user_db() -> None:
    if USER_DB_FILE.exists():
        return
    save_users(_default_users())


def load_users() -> list[dict[str, Any]]:
    ensure_user_db()
    with USER_DB_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_users(users: list[dict[str, Any]]) -> None:
    with USER_DB_FILE.open("w", encoding="utf-8") as file:
        json.dump(users, file, indent=2)


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    safe_keys = [
        "user_id",
        "full_name",
        "employee_id",
        "email",
        "department",
        "role",
        "role_locked",
        "admin_created",
        "created_at",
    ]
    return {key: user.get(key) for key in safe_keys}


def find_user_by_email(email: str) -> dict[str, Any] | None:
    target = normalize_email(email)
    for user in load_users():
        if normalize_email(user["email"]) == target:
            return user
    return None


def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    user = find_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user.get("password_hash", "")):
        return None
    return public_user(user)


def create_employee_user(
    *,
    full_name: str,
    employee_id: str,
    email: str,
    department: str,
    password: str,
) -> tuple[bool, str, dict[str, Any] | None]:
    users = load_users()
    normalized_email = normalize_email(email)
    normalized_employee_id = employee_id.strip().upper()

    if any(normalize_email(user["email"]) == normalized_email for user in users):
        return False, "An account already exists for this email.", None

    if any(user["employee_id"].upper() == normalized_employee_id for user in users):
        return False, "An account already exists for this employee ID.", None

    password_issues = validate_password_strength(password)
    if password_issues:
        return False, "Password must include " + ", ".join(password_issues) + ".", None

    user = {
        "user_id": str(uuid4()),
        "full_name": full_name.strip(),
        "employee_id": normalized_employee_id,
        "email": normalized_email,
        "department": department.strip(),
        "role": "employee",
        "role_locked": True,
        "admin_created": False,
        "password_hash": hash_password(password),
        "created_at": _now_iso(),
    }
    users.append(user)
    save_users(users)
    return True, "Employee signup successful. Please sign in.", public_user(user)
