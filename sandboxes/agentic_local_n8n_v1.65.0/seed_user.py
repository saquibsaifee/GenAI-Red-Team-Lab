import os
import sqlite3

import tomlkit


def load_config():
    """Load configuration from config.toml."""
    config_path = os.path.join(os.path.dirname(__file__), "config.toml")
    try:
        with open(config_path, "r") as f:
            return tomlkit.load(f)
    except Exception as e:
        print(f"[-] Error loading config.toml: {e}")
        return None


def seed_database():
    """Seeds the n8n SQLite database with a target admin user."""
    """Seeds the n8n SQLite database with target users."""
    db_path = os.path.join(os.path.dirname(__file__), "data", "database.sqlite")

    config = load_config()
    if not config:
        return

    users = config.get("users", [])
    if not users:
        print("[-] No users found in config.toml")
        return

    print(f"[*] Seeding database at: {db_path}")

    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        import time

        # Poll for table existence (n8n creates it during migrations)
        print("[*] Waiting for n8n to create 'user' table...")
        table_exists = False
        for _ in range(30):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='user';"
                )
                if cursor.fetchone():
                    table_exists = True
                    conn.close()
                    break
                conn.close()
            except Exception:
                pass
            time.sleep(2)

        if not table_exists:
            print("[-] Timeout: 'user' table was not created by n8n in time.")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Determine correct role column name
        cursor.execute("PRAGMA table_info('user')")
        cols = [c[1] for c in cursor.fetchall()]
        role_col = "roleSlug" if "roleSlug" in cols else "role"
        print(f"[*] Detected role column: {role_col}")

        # Batch check for existing users
        emails = [user.get("email") for user in users if user.get("email")]
        existing_emails = set()
        if emails:
            placeholders = ",".join("?" * len(emails))
            cursor.execute(
                f"SELECT email FROM user WHERE email IN ({placeholders})", tuple(emails)
            )
            existing_emails = {row[0] for row in cursor.fetchall()}

        users_to_insert = []
        for user in users:
            email = user.get("email")
            if email in existing_emails:
                print(f"[*] User '{email}' already exists. Skipping insertion.")
            else:
                user_id = user.get("id")
                first_name = user.get("first_name")
                pwd_hash = user.get("password_hash")
                role_id = user.get("global_role_id")

                users_to_insert.append(
                    (
                        user_id,
                        email,
                        first_name,
                        "System",  # lastName
                        pwd_hash,
                        role_id,
                        "{}",
                        0,
                        0,
                    )
                )
                print(f"[+] Added user to insertion batch: {email}")

        if users_to_insert:
            cursor.executemany(
                f"""
                INSERT INTO user (id, email, firstName, lastName, password, {role_col}, settings, mfaEnabled, disabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                users_to_insert,
            )
            print(f"[+] Successfully inserted {len(users_to_insert)} users.")

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"[-] Failed to seed database: {e}")


if __name__ == "__main__":
    seed_database()
