import sqlite3
import bcrypt
from getpass import getpass

DB_PATH = "database/namma_krushi.db"  # Update if your DB is elsewhere

username = "sindhu"

new_password = getpass("Enter your new admin password: ")
confirm_password = getpass("Confirm your new password: ")

if len(new_password) < 8:
    print("Password must contain at least 8 characters.")
    raise SystemExit

if new_password != confirm_password:
    print("Passwords do not match.")
    raise SystemExit

password_hash = bcrypt.hashpw(
    new_password.encode("utf-8"),
    bcrypt.gensalt()
).decode("utf-8")

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

cursor.execute(
    "UPDATE admins SET password_hash = ? WHERE username = ?",
    (password_hash, username)
)

if cursor.rowcount == 1:
    connection.commit()
    print("Admin password reset successfully!")
else:
    connection.rollback()
    print("Admin account not found. Check the database path and username.")

connection.close()