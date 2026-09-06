"""Executa os casos de `parte-1-casos.json` contra o assistente e grava as respostas cruas.

Não pontua nada: a rubrica é aplicada por uma pessoa sobre os arquivos gerados.
Uso: uv run python ia/evals/rodar_parte_1.py --base-url http://127.0.0.1:5203 --saida ia/evals/rodada-001
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import uuid

import httpx

RAIZ = pathlib.Path(__file__).resolve().parent


def enviar(cliente: httpx.Client, origem: str, writing_id: str, pergunta: str) -> dict:
    """Envia uma pergunta e consome o SSE até o quadro terminal. Uma tentativa, sem retry."""
    partes: list[str] = []
    eventos: list[dict] = []
    nome = ""
    with cliente.stream(
        "POST",
        f"/api/writings/{writing_id}/conversation/messages",
        json={"content": pergunta},
        headers={"Origin": origem, "Idempotency-Key": str(uuid.uuid4())},
        timeout=180.0,
    ) as resposta:
        resposta.raise_for_status()
        for linha in resposta.iter_lines():
            if linha.startswith("event: "):
                nome = linha[7:]
            elif linha.startswith("data: "):
                dados = json.loads(linha[6:])
                eventos.append({"event": nome, "data": dados})
                if nome == "response.delta":
                    partes.append(dados["delta"])
    return {"texto": "".join(partes), "eventos": eventos}


def main() -> int:
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--base-url", default="http://127.0.0.1:5203")
    argumentos.add_argument("--saida", default=str(RAIZ / "rodada-001"))
    opcoes = argumentos.parse_args()

    origem = opcoes.base_url
    saida = pathlib.Path(opcoes.saida)
    saida.mkdir(parents=True, exist_ok=True)
    casos = json.loads((RAIZ / "parte-1-casos.json").read_text(encoding="utf-8"))

    with httpx.Client(base_url=opcoes.base_url, timeout=30.0) as cliente:
        cliente.post(
            "/api/auth/session",
            json={
                "email": os.environ["AUTHOR_EMAIL"],
                "password": os.environ["AUTHOR_PASSWORD"],
            },
        ).raise_for_status()
        livro = cliente.post(
            "/api/books",
            json={"title": "Rodada de avaliação — Parte 1", "author": "vários"},
            headers={"Origin": origem, "Idempotency-Key": str(uuid.uuid4())},
        )
        livro.raise_for_status()
        book_id = livro.json()["id"]

        for caso in casos:
            escrita = cliente.post(
                f"/api/books/{book_id}/writings",
                json={
                    "title": caso["id"],
                    "sourceRange": "caso de avaliação",
                    "markdown": caso["markdown"],
                },
                headers={"Origin": origem, "Idempotency-Key": str(uuid.uuid4())},
            )
            escrita.raise_for_status()
            writing_id = escrita.json()["id"]

            resultado = enviar(cliente, origem, writing_id, caso["question"])
            resultado["writingId"] = writing_id
            (saida / f"{caso['id']}.json").write_text(
                json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (saida / f"{caso['id']}.md").write_text(
                f"# {caso['id']}\n\n## Pergunta\n\n{caso['question']}\n\n"
                f"## Resposta\n\n{resultado['texto']}\n",
                encoding="utf-8",
            )
            terminal = resultado["eventos"][-1]["event"] if resultado["eventos"] else "vazio"
            print(f"{caso['id']}: {terminal}, {len(resultado['texto'])} caracteres")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
