"""
Script to create or promote an admin superuser account.
Usage:
    python -m app.scripts.make_admin admin@example.com [optional_password]
"""

import sys
from app.db.session import SessionLocal
from app.models.user import User
from app.services.auth_service import get_password_hash


def make_admin(email: str, password: str = "AdminPass123!"):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user:
            user.is_superuser = True
            user.is_active = True
            if password:
                user.hashed_password = get_password_hash(password)
            db.commit()
            print(f"SUCCESS: Promoted existing user '{email}' to SUPERUSER / ADMIN!")
        else:
            user = User(
                email=email.lower(),
                hashed_password=get_password_hash(password),
                full_name="System Administrator",
                is_active=True,
                is_superuser=True
            )
            db.add(user)
            db.commit()
            print(f"SUCCESS: Created new SUPERUSER / ADMIN '{email}' with password '{password}'!")
    finally:
        db.close()


if __name__ == "__main__":
    target_email = sys.argv[1] if len(sys.argv) > 1 else "admin@test.com"
    target_pass = sys.argv[2] if len(sys.argv) > 2 else "admin12345"
    make_admin(target_email, target_pass)
