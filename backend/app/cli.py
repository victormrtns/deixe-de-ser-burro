from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys

from app.auth.service import bootstrap_author
from app.db import get_database
from app.errors import AppError
from app.publishing.cleanup import CleanupRunner


def read_bootstrap_credentials() -> tuple[str, str]:
    email = os.getenv("AUTHOR_EMAIL") or input("E-mail do autor: ")
    password = os.getenv("AUTHOR_PASSWORD") or getpass.getpass("Senha do autor: ")
    return email, password


async def bootstrap_author_command() -> int:
    email, password = read_bootstrap_credentials()
    database = get_database()
    try:
        async with database.session() as session:
            await bootstrap_author(session, email, password)
    finally:
        await database.dispose()
    print("Autor criado.")
    return 0


async def cleanup_due_publications_command(limit: int) -> int:
    database = get_database()
    try:
        result = await CleanupRunner(database).run_batch(limit=limit)
    finally:
        await database.dispose()
    print(f"Limpezas concluídas: {len(result.completed_ids)}")
    print(f"Limpezas com falha: {len(result.failed_ids)}")
    if result.failure_kinds:
        print("Falhas:", ", ".join(sorted(set(result.failure_kinds))), file=sys.stderr)
    return 1 if result.failed_ids else 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("bootstrap-author")
    cleanup = subcommands.add_parser("cleanup-due-publications")
    cleanup.add_argument("--limit", type=int, default=100)
    arguments = parser.parse_args()

    try:
        if arguments.command == "bootstrap-author":
            exit_code = asyncio.run(bootstrap_author_command())
        else:
            exit_code = asyncio.run(cleanup_due_publications_command(arguments.limit))
    except AppError as error:
        parser.exit(1, f"Erro: {error.message}\n")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
