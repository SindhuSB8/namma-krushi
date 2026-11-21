import bcrypt
from database.db import execute, fetch_one

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except (ValueError, TypeError):
        return False

def register_farmer(name, username, password, language):
    from services.validation import clean_name
    if not all([(name or "").strip(), (username or "").strip(), password]):
        return False, "fields_required"
    name, name_error = clean_name(name)
    if name_error:
        return False, name_error
    if len(password) < 6:
        return False, "password_too_short"
    try:
        user_id = execute("INSERT INTO users(name, username, password_hash, language) VALUES(?,?,?,?)",
                          (name, username.strip(), hash_password(password), language))
        return True, user_id
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            return False, "username_taken"
        return False, "account_error"

def login_farmer(username, password):
    user = fetch_one("SELECT * FROM users WHERE username = ?", (username.strip(),))
    return user if user and verify_password(password, user["password_hash"]) else None

def admin_exists(): return fetch_one("SELECT admin_id FROM admins LIMIT 1") is not None
def create_admin(username, password):
    if admin_exists(): return False, "An administrator already exists."
    if not username.strip() or len(password) < 8: return False, "Use a username and an 8-character password."
    try:
        execute("INSERT INTO admins(username,password_hash) VALUES (?,?)", (username.strip(), hash_password(password)))
        return True, "Administrator created."
    except Exception: return False, "Could not create administrator."
def login_admin(username, password):
    admin = fetch_one("SELECT * FROM admins WHERE username=?", (username.strip(),))
    return admin if admin and verify_password(password, admin["password_hash"]) else None
