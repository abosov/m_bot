from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_WEBP_RIFF_MAGIC = b"RIFF"
_WEBP_MAGIC = b"WEBP"

_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def _is_supported_image_magic(raw: bytes) -> bool:
    if raw.startswith(_JPEG_MAGIC):
        return True
    if raw.startswith(_PNG_MAGIC):
        return True
    if len(raw) >= 12 and raw.startswith(_WEBP_RIFF_MAGIC) and raw[8:12] == _WEBP_MAGIC:
        return True
    return False


def process_specialist_profile_photo(
    raw: bytes,
    *,
    max_decoded_pixels: int = 20_000_000,
) -> tuple[bytes, int, int, str]:
    if not raw or not _is_supported_image_magic(raw):
        raise ValueError("invalid_image")

    previous_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = max_decoded_pixels
    try:
        with Image.open(BytesIO(raw)) as opened:
            image_format = (opened.format or "").upper()
            if image_format not in _ALLOWED_FORMATS:
                raise ValueError("invalid_image")

            width, height = opened.size
            if width <= 0 or height <= 0 or width * height > max_decoded_pixels:
                raise ValueError("invalid_image")

            normalized = ImageOps.exif_transpose(opened)

        src_w, src_h = normalized.size
        target_ratio = 4 / 5
        current_ratio = src_w / src_h
        if current_ratio > target_ratio:
            crop_w = int(round(src_h * target_ratio))
            crop_h = src_h
            left = (src_w - crop_w) // 2
            top = 0
        else:
            crop_w = src_w
            crop_h = int(round(src_w / target_ratio))
            left = 0
            top = (src_h - crop_h) // 2

        cropped = normalized.crop((left, top, left + crop_w, top + crop_h))
        resized = cropped.resize((800, 1000), Image.Resampling.LANCZOS)
        converted = resized.convert("RGB")
        output = BytesIO()
        converted.save(output, format="JPEG", quality=85, optimize=True)
        return output.getvalue(), 800, 1000, "image/jpeg"
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("invalid_image") from exc
    finally:
        Image.MAX_IMAGE_PIXELS = previous_limit

