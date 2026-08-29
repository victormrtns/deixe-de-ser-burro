from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.files.local import LocalFileStore
from app.files.service import FileTooLarge, InvalidFileKey, UnsupportedImage

MAX_BYTES = 100_000


@pytest.fixture
def store(tmp_path: Path) -> LocalFileStore:
    return LocalFileStore(tmp_path, max_bytes=MAX_BYTES)


def png_bytes(width: int = 4, height: int = 4) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color=(200, 40, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


def jpeg_bytes_with_exif() -> bytes:
    buffer = BytesIO()
    image = Image.new("RGB", (4, 4), color=(10, 120, 10))
    exif = image.getexif()
    exif[0x0110] = "Private Camera Model"
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "key",
    ["../../secret", "/etc/passwd", "covers/../secret", "covers/./cover.png", "", "covers//x.png"],
)
def test_store_never_accepts_an_escaping_or_malformed_key(store: LocalFileStore, key: str) -> None:
    with pytest.raises(InvalidFileKey):
        store.path_for(key)


async def test_put_accepts_a_real_image_and_generates_an_opaque_key(
    store: LocalFileStore,
) -> None:
    stored = await store.put_private_cover(png_bytes())

    assert stored.key.startswith("covers/private/")
    assert stored.key.endswith(".png")
    assert stored.media_type == "image/png"
    assert store.path_for(stored.key).exists()


async def test_put_rejects_content_that_is_not_an_image(store: LocalFileStore) -> None:
    with pytest.raises(UnsupportedImage):
        await store.put_private_cover(
            b"not an image",
        )


async def test_put_rejects_a_disguised_text_payload(store: LocalFileStore) -> None:
    with pytest.raises(UnsupportedImage):
        await store.put_private_cover(b"\x89PNG\r\n\x1a\nbut actually junk")


async def test_put_rejects_oversized_bytes(store: LocalFileStore) -> None:
    with pytest.raises(FileTooLarge):
        await store.put_private_cover(b"0" * (MAX_BYTES + 1))


async def test_put_rejects_oversized_pixel_dimensions(tmp_path: Path) -> None:
    generous_bytes = LocalFileStore(tmp_path, max_bytes=50_000_000, max_pixels=16)

    with pytest.raises(FileTooLarge):
        await generous_bytes.put_private_cover(png_bytes(width=5, height=5))


async def test_put_strips_metadata_by_reencoding(store: LocalFileStore) -> None:
    stored = await store.put_private_cover(jpeg_bytes_with_exif())

    saved = Image.open(store.path_for(stored.key))
    assert stored.media_type == "image/jpeg"
    assert dict(saved.getexif()) == {}


async def test_put_leaves_no_temporary_files_behind(store: LocalFileStore, tmp_path: Path) -> None:
    stored = await store.put_private_cover(png_bytes())

    files = [path for path in tmp_path.rglob("*") if path.is_file()]
    assert files == [store.path_for(stored.key)]


async def test_open_returns_the_stored_bytes(store: LocalFileStore) -> None:
    stored = await store.put_private_cover(png_bytes())

    content = await store.open(stored.key)

    assert Image.open(BytesIO(content)).format == "PNG"


async def test_open_a_missing_key_raises_invalid_key(store: LocalFileStore) -> None:
    with pytest.raises(InvalidFileKey):
        await store.open("covers/private/00000000000000000000000000000000.png")


async def test_delete_is_idempotent(store: LocalFileStore) -> None:
    stored = await store.put_private_cover(png_bytes())

    await store.delete(stored.key)
    await store.delete(stored.key)

    assert not store.path_for(stored.key).exists()


async def test_copy_public_duplicates_the_private_cover(store: LocalFileStore) -> None:
    private = await store.put_private_cover(png_bytes())

    public = await store.copy_public(private.key)

    assert public.key.startswith("covers/public/")
    assert store.path_for(private.key).exists()
    assert store.path_for(public.key).read_bytes() == store.path_for(private.key).read_bytes()
