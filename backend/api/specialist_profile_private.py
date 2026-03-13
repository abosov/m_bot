from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

import config
from database import BillingPaymentStatus
from backend.schemas.specialist_profile_private import (
    SpecialistProfileMediaListResponse,
    SpecialistProfilePrivateResponse,
    SpecialistProfilePrivateUpdateRequest,
    SpecialistProfilePublishResponse,
    SpecialistSubscriptionPaymentStartRequest,
    SpecialistSubscriptionPaymentStartResponse,
    SpecialistProfileUploadResponse,
)
import database
from services import web_session
from services.billing import BillingError, start_specialist_subscription_payment
from services.image_pipeline import process_specialist_profile_photo
from services.media_storage import (
    promote_staged_file,
    remove_file_if_exists,
    save_upload_file_atomic,
    stage_bytes_temp,
)
from services.specialist_profile_private import (
    add_specialist_profile_document,
    list_specialist_profile_media,
    read_specialist_profile_draft,
    publish_specialist_profile,
    replace_specialist_profile_photo,
    delete_specialist_profile_photo,
    unpublish_specialist_profile,
    update_specialist_profile_draft,
)


router = APIRouter(prefix="/api/specialist/profile", tags=["specialist-profile-private"])

_ALLOWED_PHOTO_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
_ALLOWED_DOCUMENT_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}


def require_web_auth_session(request: Request) -> tuple[UUID, int]:
    cookie_value = request.cookies.get(config.WEB_CONNECT_COOKIE_NAME, "")
    verified_session = web_session.verify_session_cookie(cookie_value)
    if verified_session is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    return verified_session


@router.get("", response_model=SpecialistProfilePrivateResponse)
async def get_specialist_profile(
    verified_session: tuple[UUID, int] = Depends(require_web_auth_session),
) -> SpecialistProfilePrivateResponse:
    specialist_id, _tg_user_id = verified_session
    async with database.async_session_factory() as session:
        payload = await read_specialist_profile_draft(session, specialist_id)
        await session.commit()
    return SpecialistProfilePrivateResponse.model_validate(payload)


@router.put("", response_model=SpecialistProfilePrivateResponse)
async def put_specialist_profile(
    request_payload: SpecialistProfilePrivateUpdateRequest,
    verified_session: tuple[UUID, int] = Depends(require_web_auth_session),
) -> SpecialistProfilePrivateResponse:
    specialist_id, _tg_user_id = verified_session

    try:
        async with database.async_session_factory() as session:
            payload = await update_specialist_profile_draft(
                session,
                specialist_id=specialist_id,
                first_name=request_payload.first_name,
                middle_name=request_payload.middle_name,
                last_name=request_payload.last_name,
                specialization=request_payload.specialization,
                hero_quote=request_payload.hero_quote,
                about=request_payload.about,
                education=request_payload.education,
                services=request_payload.services,
                reviews=request_payload.reviews,
            )
            await session.commit()
    except ValueError as exc:
        if str(exc) == "slug_generation_failed":
            raise HTTPException(status_code=409, detail="slug_generation_failed") from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SpecialistProfilePrivateResponse.model_validate(payload)



@router.post("/publish", response_model=SpecialistProfilePublishResponse)
async def post_specialist_profile_publish(
    verified_session: tuple[UUID, int] = Depends(require_web_auth_session),
) -> SpecialistProfilePublishResponse:
    specialist_id, _tg_user_id = verified_session

    try:
        async with database.async_session_factory() as session:
            payload = await publish_specialist_profile(session, specialist_id=specialist_id)
            await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SpecialistProfilePublishResponse.model_validate(payload)


@router.post("/unpublish", response_model=SpecialistProfilePublishResponse)
async def post_specialist_profile_unpublish(
    verified_session: tuple[UUID, int] = Depends(require_web_auth_session),
) -> SpecialistProfilePublishResponse:
    specialist_id, _tg_user_id = verified_session

    async with database.async_session_factory() as session:
        payload = await unpublish_specialist_profile(session, specialist_id=specialist_id)
        await session.commit()

    return SpecialistProfilePublishResponse.model_validate(payload)

def _assert_content_type(upload: UploadFile, allowed: set[str]) -> None:
    content_type = (upload.content_type or "").lower().strip()
    if content_type not in allowed:
        raise HTTPException(status_code=400, detail="invalid_content_type")


@router.post("/photo", response_model=SpecialistProfileUploadResponse)
async def upload_specialist_profile_photo(
    file: UploadFile = File(...),
    verified_session: tuple[UUID, int] = Depends(require_web_auth_session),
) -> SpecialistProfileUploadResponse:
    specialist_id, _tg_user_id = verified_session
    _assert_content_type(file, _ALLOWED_PHOTO_CONTENT_TYPES)

    try:
        raw = await file.read(config.PROFILE_PHOTO_MAX_BYTES + 1)
        await file.close()
        if len(raw) > config.PROFILE_PHOTO_MAX_BYTES:
            raise HTTPException(status_code=413, detail="file_too_large")

        normalized, _width, _height, _mime_type = process_specialist_profile_photo(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    uploads_root = Path(config.PROFILE_UPLOADS_DIR)
    file_key = f"media/specialists/{specialist_id}/profile_photo.jpg"
    staged_key = stage_bytes_temp(
        uploads_root=uploads_root,
        key_prefix=f"media/specialists/{specialist_id}",
        payload=normalized,
        suffix=".jpg.tmp",
    )

    old_keys: list[str] = []
    try:
        async with database.async_session_factory() as session:
            old_keys = await replace_specialist_profile_photo(
                session,
                specialist_id=specialist_id,
                file_key=file_key,
                title="Фото",
            )
            await session.commit()
    except Exception:
        remove_file_if_exists(uploads_root=uploads_root, file_key=staged_key)
        raise

    promote_staged_file(uploads_root=uploads_root, staged_key=staged_key, final_key=file_key)

    for old_key in old_keys:
        if old_key != file_key:
            remove_file_if_exists(uploads_root=uploads_root, file_key=old_key)

    return SpecialistProfileUploadResponse(ok=True)


@router.delete("/photo", response_model=SpecialistProfileUploadResponse)
async def delete_specialist_profile_photo_endpoint(
    verified_session: tuple[UUID, int] = Depends(require_web_auth_session),
) -> SpecialistProfileUploadResponse:
    specialist_id, _tg_user_id = verified_session
    uploads_root = Path(config.PROFILE_UPLOADS_DIR)

    async with database.async_session_factory() as session:
        old_keys = await delete_specialist_profile_photo(session, specialist_id=specialist_id)
        await session.commit()

    for old_key in old_keys:
        remove_file_if_exists(uploads_root=uploads_root, file_key=old_key)

    return SpecialistProfileUploadResponse(ok=True)

@router.post("/documents", response_model=SpecialistProfileUploadResponse)
async def upload_specialist_profile_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    verified_session: tuple[UUID, int] = Depends(require_web_auth_session),
) -> SpecialistProfileUploadResponse:
    specialist_id, _tg_user_id = verified_session
    _assert_content_type(file, _ALLOWED_DOCUMENT_CONTENT_TYPES)

    try:
        file_key, safe_filename = await save_upload_file_atomic(
            file,
            uploads_root=Path(config.PROFILE_UPLOADS_DIR),
            key_prefix=f"specialist/{specialist_id}/docs",
            max_bytes=config.PROFILE_DOCUMENT_MAX_BYTES,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    media_title = (title or "").strip() or safe_filename
    async with database.async_session_factory() as session:
        await add_specialist_profile_document(
            session,
            specialist_id=specialist_id,
            file_key=file_key,
            title=media_title,
        )
        await session.commit()

    return SpecialistProfileUploadResponse(ok=True)


@router.get("/media", response_model=SpecialistProfileMediaListResponse)
async def get_specialist_profile_media(
    verified_session: tuple[UUID, int] = Depends(require_web_auth_session),
) -> SpecialistProfileMediaListResponse:
    specialist_id, _tg_user_id = verified_session
    async with database.async_session_factory() as session:
        items = await list_specialist_profile_media(session, specialist_id=specialist_id)
        await session.commit()
    return SpecialistProfileMediaListResponse(items=items)


@router.post("/billing/subscription-payment", response_model=SpecialistSubscriptionPaymentStartResponse)
async def post_specialist_subscription_payment_start(
    request_payload: SpecialistSubscriptionPaymentStartRequest,
    verified_session: tuple[UUID, int] = Depends(require_web_auth_session),
) -> SpecialistSubscriptionPaymentStartResponse:
    specialist_id, _tg_user_id = verified_session

    try:
        result = await start_specialist_subscription_payment(
            specialist_id=specialist_id,
            tariff_code=request_payload.tariff_code,
            return_url=request_payload.return_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except BillingError as exc:
        detail = str(exc)
        if detail in {"tariff_code_required", "tariff_not_found", "tariff_inactive"}:
            raise HTTPException(status_code=422, detail=detail) from exc
        if detail == "payment_not_retriable":
            raise HTTPException(status_code=409, detail=detail) from exc
        raise HTTPException(status_code=502, detail=detail) from exc

    if result.status != BillingPaymentStatus.pending or not result.confirmation_url:
        raise HTTPException(status_code=502, detail="payment_start_failed")

    return SpecialistSubscriptionPaymentStartResponse(
        payment_id=str(result.payment_id),
        tariff_code=request_payload.tariff_code,
        payment_status=result.status.value,
        requires_redirect=True,
        confirmation_url=result.confirmation_url,
    )
