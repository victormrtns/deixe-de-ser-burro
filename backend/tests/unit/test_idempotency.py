from __future__ import annotations

from pydantic import BaseModel

from app.idempotency.service import canonical_request_hash


class ExamplePayload(BaseModel):
    title: str
    author: str


def test_equal_payloads_produce_the_same_hash() -> None:
    first = canonical_request_hash(ExamplePayload(title="Duna", author="Frank Herbert"))
    second = canonical_request_hash(ExamplePayload(title="Duna", author="Frank Herbert"))

    assert first == second
    assert len(first) == 64


def test_different_payloads_produce_different_hashes() -> None:
    original = canonical_request_hash(ExamplePayload(title="Duna", author="Frank Herbert"))
    changed = canonical_request_hash(ExamplePayload(title="Duna Messias", author="Frank Herbert"))

    assert original != changed
