import base64
import hashlib
import secrets
import streamlit as st

from services.mongo_store import ensure_indexes, get_db


def normalize_email(email: str) -> str:
	return email.strip().lower()


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
	if salt is None:
		salt = secrets.token_hex(16)
	derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
	return salt, base64.b64encode(derived_key).decode("utf-8")


def register_user(name: str, email: str, password: str) -> dict:
	ensure_indexes()
	db = get_db()
	email = normalize_email(email)
	if db.users.find_one({"email": email}):
		raise ValueError("An account with this email already exists.")

	salt, password_hash = hash_password(password)
	result = db.users.insert_one(
		{
			"name": name.strip(),
			"email": email,
			"password_salt": salt,
			"password_hash": password_hash,
		}
	)
	return {"user_id": str(result.inserted_id), "name": name.strip(), "email": email}


def authenticate_user(email: str, password: str):
	ensure_indexes()
	db = get_db()
	user = db.users.find_one({"email": normalize_email(email)})
	if not user:
		return None
	_, password_hash = hash_password(password, user.get("password_salt", ""))
	if password_hash != user.get("password_hash"):
		return None
	return {"user_id": str(user["_id"]), "name": user.get("name", "User"), "email": user.get("email", "")}


def set_current_user(user: dict):
	st.session_state.authenticated = True
	st.session_state.current_user = user


def get_current_user():
	if st.session_state.get("authenticated") and st.session_state.get("current_user"):
		return st.session_state.current_user
	return None


def is_authenticated() -> bool:
	return get_current_user() is not None


def logout_user():
	for key in ["authenticated", "current_user", "messages", "current_transaction", "form_submitted", "save_clicked"]:
		st.session_state.pop(key, None)
