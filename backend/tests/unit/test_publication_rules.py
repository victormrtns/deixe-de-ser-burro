from __future__ import annotations

import pytest

from app.publishing.service import excerpt_from_markdown, reading_minutes, slugify

LONG_MARKDOWN = "# Título\n\n" + " ".join(["palavra"] * 700)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Ritual antes do foco", "ritual-antes-do-foco"),
        ("  Atenção, coragem & profundidade!  ", "atencao-coragem-profundidade"),
        ("O DESERTO --- profundo", "o-deserto-profundo"),
        ("çãéü", "caeu"),
    ],
)
def test_slugify_produces_canonical_public_slugs(title: str, expected: str) -> None:
    assert slugify(title) == expected


def test_slugify_falls_back_when_no_characters_survive() -> None:
    assert slugify("!!! ???") == "artigo"


def test_excerpt_strips_markdown_syntax_and_truncates_at_a_word_boundary() -> None:
    markdown = "# Título\n\n**Uma** ideia [central](https://example.com) `sobre` foco.\n\nResto."

    excerpt = excerpt_from_markdown(markdown)

    assert excerpt.startswith("Uma ideia central sobre foco.")
    assert "#" not in excerpt
    assert "*" not in excerpt
    assert "](" not in excerpt


def test_excerpt_of_a_long_document_stays_within_the_limit() -> None:
    excerpt = excerpt_from_markdown(LONG_MARKDOWN)

    assert len(excerpt) <= 220
    assert excerpt.endswith("…")


def test_reading_minutes_never_reports_less_than_one_minute() -> None:
    assert reading_minutes("# Só um título") == 1
    assert reading_minutes(LONG_MARKDOWN) == 4
