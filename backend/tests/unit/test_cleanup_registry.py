from __future__ import annotations

from sqlalchemy.dialects import postgresql

from app.publishing.cleanup import due_publications_query


def test_the_due_query_claims_rows_with_skip_locked() -> None:
    sql = str(due_publications_query(limit=5).compile(dialect=postgresql.dialect())).lower()

    assert "for update skip locked" in sql
    assert "cleanup_due_at" in sql
    assert "cleanup_cancelled_at is null" in sql
    assert "cleanup_completed_at is null" in sql
    assert "state = " in sql
