import io

import pytest
from PIL import Image

from services.image_pipeline import process_specialist_profile_photo


def _make_image_bytes(fmt: str, size: tuple[int, int], color=(120, 140, 160)) -> bytes:
    image = Image.new("RGB", size, color)
    buf = io.BytesIO()
    image.save(buf, format=fmt)
    return buf.getvalue()


@pytest.mark.parametrize(
    ("fmt", "size"),
    [
        ("JPEG", (1600, 1000)),
        ("PNG", (1000, 1600)),
        ("WEBP", (1200, 1500)),
    ],
)
def test_process_profile_photo_normalizes_to_jpeg_800x1000(fmt, size):
    payload = _make_image_bytes(fmt, size)
    normalized, width, height, mime_type = process_specialist_profile_photo(payload)

    assert width == 800
    assert height == 1000
    assert mime_type == "image/jpeg"

    result = Image.open(io.BytesIO(normalized))
    assert result.format == "JPEG"
    assert result.size == (800, 1000)


def test_process_profile_photo_rejects_invalid_file():
    with pytest.raises(ValueError, match="invalid_image"):
        process_specialist_profile_photo(b"not-an-image")
