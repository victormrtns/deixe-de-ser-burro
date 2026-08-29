from __future__ import annotations

import pytest

from app.errors import AppError
from app.writings.schemas import WritingMetadataRequest, WritingSaveRequest
from app.writings.service import _decode_cursor, _encode_cursor


def test_version_cursor_round_trips() -> None:
    cursor = _encode_cursor(42)

    assert _decode_cursor(cursor) == 42
    assert _decode_cursor(None) is None


@pytest.mark.parametrize("cursor", ["not-base64!", "aGVsbG8=", "LTU="])
def test_malformed_and_non_positive_cursors_are_validation_errors(cursor: str) -> None:
    with pytest.raises(AppError) as raised:
        _decode_cursor(cursor)

    assert raised.value.code == "validation_error"
    assert raised.value.status_code == 400


def test_write_requests_accept_the_camel_case_frontend_contract() -> None:
    save = WritingSaveRequest.model_validate({"markdown": "# Novo", "expectedVersion": 3})
    metadata = WritingMetadataRequest.model_validate({"title": "Novo título", "expectedVersion": 3})

    assert save.expected_version == 3
    assert metadata.title == "Novo título"
    assert metadata.source_range is None
