from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import ALLOWED_ORIGIN

MUTATION_HEADERS = {"Origin": ALLOWED_ORIGIN}


async def create_book(client: AsyncClient, title: str, author: str = "Frank Herbert") -> str:
    response = await client.post(
        "/api/books", headers=MUTATION_HEADERS, json={"title": title, "author": author}
    )
    return str(response.json()["id"])


async def create_writing(client: AsyncClient, book_id: str, title: str) -> str:
    response = await client.post(
        f"/api/books/{book_id}/writings",
        headers=MUTATION_HEADERS,
        json={"title": title, "sourceRange": "Cap. 1", "markdown": f"# {title}\n\nUm ensaio."},
    )
    return str(response.json()["id"])


async def publish(client: AsyncClient, writing_id: str, key: str) -> str:
    response = await client.post(
        f"/api/writings/{writing_id}/publication",
        headers={**MUTATION_HEADERS, "Idempotency-Key": key},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["slug"])


async def test_the_landing_is_honestly_empty_without_publications(client: AsyncClient) -> None:
    landing = await client.get("/api/public/landing")

    assert landing.status_code == 200
    assert landing.json() == {
        "featuredArticle": None,
        "recentArticles": [],
        "publishedBooks": [],
    }


async def test_the_featured_article_falls_back_to_the_newest_publication(
    authenticated_client: AsyncClient, client: AsyncClient, session: AsyncSession
) -> None:
    book_id = await create_book(authenticated_client, "Duna")
    older = await create_writing(authenticated_client, book_id, "Primeiro ensaio")
    newer = await create_writing(authenticated_client, book_id, "Segundo ensaio")
    older_slug = await publish(authenticated_client, older, "publish-1")
    newer_slug = await publish(authenticated_client, newer, "publish-2")
    await session.execute(
        text(
            "UPDATE publications SET published_at = published_at - interval '1 day'"
            " WHERE slug = :slug"
        ),
        {"slug": older_slug},
    )
    await session.commit()

    landing = (await client.get("/api/public/landing")).json()

    assert landing["featuredArticle"]["slug"] == newer_slug
    assert [item["slug"] for item in landing["recentArticles"]] == [newer_slug, older_slug]


async def test_the_editorial_choice_overrides_the_fallback(
    authenticated_client: AsyncClient, client: AsyncClient, session: AsyncSession
) -> None:
    book_id = await create_book(authenticated_client, "Duna")
    older = await create_writing(authenticated_client, book_id, "Primeiro ensaio")
    newer = await create_writing(authenticated_client, book_id, "Segundo ensaio")
    older_slug = await publish(authenticated_client, older, "publish-1")
    await publish(authenticated_client, newer, "publish-2")
    await session.execute(
        text(
            "UPDATE publications SET published_at = published_at - interval '1 day'"
            " WHERE slug = :slug"
        ),
        {"slug": older_slug},
    )
    await session.commit()
    chosen = await authenticated_client.put(
        "/api/editorial/featured-publication", headers=MUTATION_HEADERS, json={"slug": older_slug}
    )
    assert chosen.status_code == 204

    landing = (await client.get("/api/public/landing")).json()

    assert landing["featuredArticle"]["slug"] == older_slug


async def test_books_appear_publicly_only_with_an_active_publication(
    authenticated_client: AsyncClient, client: AsyncClient
) -> None:
    published_book = await create_book(authenticated_client, "Duna")
    private_book = await create_book(authenticated_client, "Livro sem publicação")
    await create_writing(authenticated_client, private_book, "Rascunho privado")
    writing = await create_writing(authenticated_client, published_book, "O deserto")
    await publish(authenticated_client, writing, "publish-1")

    books = (await client.get("/api/public/books")).json()

    assert [book["slug"] for book in books] == ["duna"]
    assert books[0]["publishedArticleCount"] == 1
    assert books[0]["latestArticle"]["slug"] == "o-deserto"


async def test_withdrawn_articles_disappear_from_every_public_route(
    authenticated_client: AsyncClient, client: AsyncClient
) -> None:
    book_id = await create_book(authenticated_client, "Duna")
    writing = await create_writing(authenticated_client, book_id, "O deserto")
    slug = await publish(authenticated_client, writing, "publish-1")
    await authenticated_client.delete(
        f"/api/writings/{writing}/publication", headers=MUTATION_HEADERS
    )

    landing = (await client.get("/api/public/landing")).json()
    article = await client.get(f"/api/public/articles/{slug}")
    books = (await client.get("/api/public/books")).json()
    book_detail = await client.get("/api/public/books/duna")

    assert landing == {"featuredArticle": None, "recentArticles": [], "publishedBooks": []}
    assert article.status_code == 404
    assert books == []
    assert book_detail.status_code == 404


async def test_editing_the_draft_after_publishing_does_not_change_the_article(
    authenticated_client: AsyncClient, client: AsyncClient
) -> None:
    book_id = await create_book(authenticated_client, "Duna")
    writing = await create_writing(authenticated_client, book_id, "O deserto")
    slug = await publish(authenticated_client, writing, "publish-1")
    await authenticated_client.put(
        f"/api/writings/{writing}",
        headers=MUTATION_HEADERS,
        json={"markdown": "# Rascunho novo", "expectedVersion": 1},
    )

    article = (await client.get(f"/api/public/articles/{slug}")).json()

    assert article["markdown"] == "# O deserto\n\nUm ensaio."


async def test_the_book_detail_lists_its_articles_newest_first(
    authenticated_client: AsyncClient, client: AsyncClient, session: AsyncSession
) -> None:
    book_id = await create_book(authenticated_client, "Duna")
    first = await create_writing(authenticated_client, book_id, "Primeiro ensaio")
    second = await create_writing(authenticated_client, book_id, "Segundo ensaio")
    first_slug = await publish(authenticated_client, first, "publish-1")
    second_slug = await publish(authenticated_client, second, "publish-2")
    await session.execute(
        text(
            "UPDATE publications SET published_at = published_at - interval '1 day'"
            " WHERE slug = :slug"
        ),
        {"slug": first_slug},
    )
    await session.commit()

    detail = (await client.get("/api/public/books/duna")).json()

    assert detail["slug"] == "duna"
    assert detail["publishedArticleCount"] == 2
    assert [item["slug"] for item in detail["articles"]] == [second_slug, first_slug]
    assert detail["latestArticle"]["slug"] == second_slug


async def test_public_topics_come_only_from_publication_topics(
    authenticated_client: AsyncClient, client: AsyncClient, session: AsyncSession
) -> None:
    book_id = await create_book(authenticated_client, "Duna")
    writing = await create_writing(authenticated_client, book_id, "O deserto")
    await publish(authenticated_client, writing, "publish-1")
    await session.execute(
        text(
            "INSERT INTO publication_topics (id, publication_id, topic, position)"
            " SELECT gen_random_uuid(), id, topic, position FROM publications,"
            " (VALUES ('atenção', 0), ('ritual', 1)) AS topics(topic, position)"
        )
    )
    await session.commit()

    books = (await client.get("/api/public/books")).json()

    assert books[0]["publicTopics"] == ["atenção", "ritual"]
