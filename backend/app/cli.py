from __future__ import annotations

import argparse
import asyncio
import getpass
import os

from app.auth.service import bootstrap_author
from app.db import get_database
from app.errors import AppError


def read_bootstrap_credentials() -> tuple[str, str]:
    email = os.getenv("AUTHOR_EMAIL") or input("E-mail do autor: ")
    password = os.getenv("AUTHOR_PASSWORD") or getpass.getpass("Senha do autor: ")
    return email, password


async def bootstrap_author_command() -> None:
    email, password = read_bootstrap_credentials()
    database = get_database()
    try:
        async with database.session() as session:
            await bootstrap_author(session, email, password)
    finally:
        await database.dispose()
    print("Autor criado.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    parser.add_argument("command", choices=["bootstrap-author"])
    arguments = parser.parse_args()

    try:
        if arguments.command == "bootstrap-author":
            asyncio.run(bootstrap_author_command())
    except AppError as error:
        parser.exit(1, f"Erro: {error.message}\n")


if __name__ == "__main__":
    main()
