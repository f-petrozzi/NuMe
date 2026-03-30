"""
Garmin OAuth bootstrap script.
Run once per user account to generate and cache OAuth tokens.

Usage:
    cd apps/api
    python ../../scripts/garmin_bootstrap.py --user-id <user_id>

    # Override credentials (defaults to GARMIN_USERNAME/GARMIN_PASSWORD from .env)
    python ../../scripts/garmin_bootstrap.py --user-id 1 --email me@example.com

Tokens are written to GARMIN_TOKEN_DIR/<user_id>/ (mode 700).
After bootstrap, start the API normally — sync runs automatically.
"""
from __future__ import annotations

import argparse
import os
import sys

# Make apps/api importable
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.join(SCRIPT_DIR, "..", "apps", "api")
sys.path.insert(0, API_DIR)

from settings import settings


def _ensure_private_dir(path: str) -> None:
    os.makedirs(path, mode=0o700, exist_ok=True)
    os.chmod(path, 0o700)


def bootstrap(user_id: int, email: str, password: str) -> None:
    try:
        from garminconnect import Garmin  # type: ignore[import]
    except ImportError:
        sys.exit("garminconnect is not installed. Run: pip install garminconnect")

    token_dir = os.path.join(settings.garmin_token_dir, str(user_id))
    staging_dir = token_dir + ".tmp"

    _ensure_private_dir(settings.garmin_token_dir)
    _ensure_private_dir(staging_dir)

    print(f"Authenticating {email} for user_id={user_id}...")

    def _prompt_mfa() -> str:
        return input("Enter Garmin MFA code: ").strip()

    client = Garmin(email=email, password=password, is_cn=False, prompt_mfa=_prompt_mfa)
    client.login()
    client.garth.dump(staging_dir)

    # Atomic move: staging → final
    import shutil
    if os.path.exists(token_dir):
        shutil.rmtree(token_dir)
    os.rename(staging_dir, token_dir)
    os.chmod(token_dir, 0o700)

    print(f"Token cache written to: {token_dir}")
    print("Bootstrap complete. Start/restart the API to activate Garmin sync.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap Garmin OAuth tokens for a user")
    parser.add_argument("--user-id", type=int, required=True, help="NüMe user ID")
    parser.add_argument("--email", default="", help="Garmin email (default: GARMIN_USERNAME)")
    parser.add_argument("--password", default="", help="Garmin password (default: GARMIN_PASSWORD)")
    args = parser.parse_args()

    email = args.email or settings.garmin_username
    password = args.password or settings.garmin_password

    if not email:
        sys.exit("Email required — pass --email or set GARMIN_USERNAME")
    if not password:
        password = input(f"Garmin password for {email}: ")
        if not password:
            sys.exit("Password required")

    bootstrap(args.user_id, email, password)


if __name__ == "__main__":
    main()
