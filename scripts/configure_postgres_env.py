"""Configure the ignored local PostgreSQL credentials without printing secrets."""

from __future__ import annotations

import argparse
import re
import secrets
from pathlib import Path


PASSWORD_PLACEHOLDER = "REPLACE_WITH_A_LOCAL_PASSWORD"


def configure_postgres_env(env_path: Path, *, password: str | None = None) -> bool:
    """Replace local password placeholders once and keep the operation idempotent."""
    content = env_path.read_text(encoding="utf-8")
    if PASSWORD_PLACEHOLDER not in content:
        return False

    local_password = password or secrets.token_urlsafe(32)
    env_path.write_text(
        content.replace(PASSWORD_PLACEHOLDER, local_password),
        encoding="utf-8",
    )
    return True


def configure_postgres_port(env_path: Path, *, port: int) -> None:
    """Update the local published port without reading or printing the password."""
    content = env_path.read_text(encoding="utf-8")
    content = re.sub(
        r"(?m)^SORABEL_POSTGRES_PORT=\d+$",
        f"SORABEL_POSTGRES_PORT={port}",
        content,
    )
    content = re.sub(r"\bport=\d+\b", f"port={port}", content)
    env_path.write_text(content, encoding="utf-8")


def _env_value(content: str, name: str, default: str) -> str:
    match = re.search(rf"(?m)^{re.escape(name)}=(.*)$", content)
    if match is None or not match.group(1).strip():
        return default
    return match.group(1).strip().strip('"')


def configure_reader_dsns(
    env_path: Path,
    *,
    support_password: str | None = None,
    commercial_password: str | None = None,
) -> bool:
    """Create distinct local DSNs for the two data-reading PostgreSQL roles."""
    content = env_path.read_text(encoding="utf-8")
    port = _env_value(content, "SORABEL_POSTGRES_PORT", "55432")
    database = _env_value(content, "SORABEL_POSTGRES_DB", "sorabel")
    changed = False

    credentials = {
        "SORABEL_SQL_SUPPORT_DSN": (
            "sorabel_support_login",
            support_password or secrets.token_urlsafe(32),
        ),
        "SORABEL_SQL_COMMERCIAL_DSN": (
            "sorabel_commercial_login",
            commercial_password or secrets.token_urlsafe(32),
        ),
    }
    for setting, (user, password) in credentials.items():
        empty_setting = rf"(?m)^{re.escape(setting)}=\s*$"
        if re.search(empty_setting, content) is None:
            continue
        dsn = f'host=localhost port={port} dbname={database} user={user} password={password}'
        content = re.sub(empty_setting, f'{setting}="{dsn}"', content)
        changed = True

    if changed:
        env_path.write_text(content, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--port", type=int)
    parser.add_argument("--readers", action="store_true")
    args = parser.parse_args()

    changed = configure_postgres_env(args.env_file)
    if changed:
        print("Local PostgreSQL credentials configured in the ignored .env file.")
    else:
        print("Local PostgreSQL credentials were already configured.")
    if args.port is not None:
        configure_postgres_port(args.env_file, port=args.port)
        print(f"Local Sorabel PostgreSQL port configured as {args.port}.")
    if args.readers:
        readers_changed = configure_reader_dsns(args.env_file)
        message = "configured" if readers_changed else "already configured"
        print(f"Profile-specific PostgreSQL credentials {message}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
