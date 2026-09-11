from __future__ import annotations

import argparse
import sys

from rdspan import config
from rdspan.db import connect, get_or_create_user, migrate
from rdspan.seed import seed


def cmd_seed(_args: argparse.Namespace) -> int:
    conn = connect()
    try:
        migrate(conn)
        stats = seed(conn)
        get_or_create_user(conn, config.basic_auth_user())
        print(f"Seeded {stats['paradigms']} paradigms, {stats['phrases']} phrases.")
        return 0
    finally:
        conn.close()


def cmd_generate_audio(args: argparse.Namespace) -> int:
    from rdspan.tts import generate_audio

    stats = generate_audio(force=args.force)
    print(f"Audio written={stats['written']} skipped={stats['skipped']}")
    return 0


def cmd_serve(_args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run(
        "rdspan.web:app",
        host=config.host(),
        port=config.port(),
        factory=False,
    )
    return 0


def cmd_migrate(_args: argparse.Namespace) -> int:
    conn = connect()
    try:
        migrate(conn)
        print(f"Migrations applied at {config.database_path()}")
        return 0
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rdspan", description="Spanish by Ranieri–Dowling")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_seed = sub.add_parser("seed", help="Load curated paradigms and phrases into SQLite")
    p_seed.set_defaults(func=cmd_seed)

    p_audio = sub.add_parser(
        "generate-audio",
        help="Pre-generate Piper WAV/OGG for every cell and phrase (not used mid-drill)",
    )
    p_audio.add_argument("--force", action="store_true", help="Regenerate even if files exist")
    p_audio.set_defaults(func=cmd_generate_audio)

    p_serve = sub.add_parser("serve", help="Run the web app")
    p_serve.set_defaults(func=cmd_serve)

    p_migrate = sub.add_parser("migrate", help="Apply SQLite migrations")
    p_migrate.set_defaults(func=cmd_migrate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
