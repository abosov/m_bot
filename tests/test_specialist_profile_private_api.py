import asyncio
import importlib
import re
import types
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text


_PRIVATE_SLUG_RE = re.compile(r"^[A-Za-z]+[A-Za-z0-9]*_[0-9]{2}$")


def _load_web_app(tmp_path, monkeypatch):
    db_path = tmp_path / "specialist_profile_private.db"
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "invalid-token")
    monkeypatch.setenv("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("BASE_URL", "http://localhost")
    monkeypatch.setenv("PUBLIC_SITE_URL", "http://localhost")

    import config
    import database
    import services.specialist_profile_private as specialist_profile_private_service
    import backend.api.specialist_profile_private as specialist_profile_private_api

    importlib.reload(config)
    database = importlib.reload(database)
    importlib.reload(specialist_profile_private_service)
    importlib.reload(specialist_profile_private_api)

    import web_server
    web_server = importlib.reload(web_server)
    return web_server, database


def test_specialist_profile_private_requires_cookie(tmp_path, monkeypatch):
    web_server, _database = _load_web_app(tmp_path, monkeypatch)
    client = TestClient(web_server.app)

    response = client.get("/api/specialist/profile")

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


async def _prepare_specialist(database):
    specialist_id = uuid.uuid4()
    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding, specialization="Психолог"))
        session.add(
            database.SpecialistProfile(
                specialist_id=specialist_id,
                public_name="Иван Иванов",
                owner_tg_user_id=777,
                owner_tg_username="spec",
                specialist_timezone="Europe/Moscow",
            )
        )
        await session.commit()

    return specialist_id


def test_first_get_creates_draft_profile_and_returns_values(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)

    response = client.get(
        "/api/specialist/profile",
        cookies={web_server.config.WEB_CONNECT_COOKIE_NAME: cookie},
    )

    assert response.status_code == 200
    assert response.json() == {
        "first_name": "Иван",
        "middle_name": "",
        "last_name": "Иванов",
        "specialization": "Психолог",
        "hero_quote": "",
        "about": "",
        "education": "",
        "services": "",
        "reviews": "",
        "public_slug": None,
        "is_published": False,
    }

    async def _assert_profile_created():
        async with database.async_session_factory() as session:
            profile = (
                await session.execute(
                    text("SELECT display_name, first_name, middle_name, last_name, is_published FROM specialist_public_profile WHERE specialist_id = :sid"),
                    {"sid": str(specialist_id)},
                )
            ).mappings().first()
            assert profile is not None
            assert profile["is_published"] in (False, 0)
            assert profile["display_name"] == "Иван Иванов"
            assert profile["first_name"] == "Иван"
            assert profile["middle_name"] is None
            assert profile["last_name"] == "Иванов"

    asyncio.run(_assert_profile_created())


def test_put_then_get_returns_updated_values(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    cookies = {web_server.config.WEB_CONNECT_COOKIE_NAME: cookie}

    payload = {
        "first_name": "Анна",
        "middle_name": "Сергеевна",
        "last_name": "Петрова",
        "specialization": "Психотерапевт",
        "hero_quote": "С заботой о вашем состоянии",
        "about": "Текст о себе",
        "education": "МГУ, факультет психологии",
        "services": "Консультация 60 минут",
        "reviews": "Очень помогли",
    }

    put_response = client.put("/api/specialist/profile", json=payload, cookies=cookies)
    assert put_response.status_code == 200

    get_response = client.get("/api/specialist/profile", cookies=cookies)
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["is_published"] is False
    assert isinstance(body["public_slug"], str)
    assert _PRIVATE_SLUG_RE.fullmatch(body["public_slug"]) is not None
    suffix = int(body["public_slug"].rsplit("_", maxsplit=1)[1])
    assert 10 <= suffix <= 30
    assert {k: v for k, v in body.items() if k not in {"public_slug", "is_published"}} == payload

    async def _assert_blocks_saved():
        async with database.async_session_factory() as session:
            profile = (
                await session.execute(
                    text("SELECT id, display_name, first_name, middle_name, last_name, specialization FROM specialist_public_profile WHERE specialist_id = :sid"),
                    {"sid": str(specialist_id)},
                )
            ).mappings().first()
            assert profile is not None
            assert profile["display_name"] == "Анна Сергеевна Петрова"
            assert profile["first_name"] == "Анна"
            assert profile["middle_name"] == "Сергеевна"
            assert profile["last_name"] == "Петрова"
            assert profile["specialization"] == "Психотерапевт"

            blocks = (
                await session.execute(
                    text("SELECT block_type, content FROM specialist_public_block WHERE profile_id = :profile_id"),
                    {"profile_id": profile["id"]},
                )
            ).mappings().all()
            by_type = {b["block_type"]: b["content"] for b in blocks}
            assert by_type == {
                "about": "Текст о себе",
                "education": "МГУ, факультет психологии",
                "services": "Консультация 60 минут",
                "reviews": "Очень помогли",
            }

    asyncio.run(_assert_blocks_saved())


def _valid_profile_payload() -> dict[str, str]:
    return {
        "first_name": "Анна",
        "middle_name": "Сергеевна",
        "last_name": "Петрова",
        "specialization": "Психотерапевт",
        "hero_quote": "С заботой о вашем состоянии",
        "about": "Текст о себе",
        "education": "МГУ, факультет психологии",
        "services": "Консультация 60 минут",
        "reviews": "Очень помогли",
    }


def test_put_profile_rejects_blank_specialization_after_trim(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    payload = _valid_profile_payload()
    payload["specialization"] = "   "

    response = client.put(
        "/api/specialist/profile",
        json=payload,
        cookies={web_server.config.WEB_CONNECT_COOKIE_NAME: cookie},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "specialization_required"}


def test_put_profile_rejects_too_long_specialization(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    payload = _valid_profile_payload()
    payload["specialization"] = "x" * 201

    response = client.put(
        "/api/specialist/profile",
        json=payload,
        cookies={web_server.config.WEB_CONNECT_COOKIE_NAME: cookie},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "specialization_too_long"}


def test_put_profile_rejects_too_long_hero_quote(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    payload = _valid_profile_payload()
    payload["hero_quote"] = "x" * 201

    response = client.put(
        "/api/specialist/profile",
        json=payload,
        cookies={web_server.config.WEB_CONNECT_COOKIE_NAME: cookie},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "hero_quote_too_long"}


def test_put_profile_rejects_too_long_about_block(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    payload = _valid_profile_payload()
    payload["about"] = "x" * 8001

    response = client.put(
        "/api/specialist/profile",
        json=payload,
        cookies={web_server.config.WEB_CONNECT_COOKIE_NAME: cookie},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "block_too_long"}


def test_put_profile_server_trims_fields_and_builds_display_name(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    cookies = {web_server.config.WEB_CONNECT_COOKIE_NAME: cookie}

    payload = _valid_profile_payload()
    payload.update(
        {
            "first_name": "  Анна  ",
            "middle_name": "  Сергеевна ",
            "last_name": "  Петрова   ",
            "specialization": "  Психолог  ",
            "hero_quote": "  С заботой  ",
            "about": "  О себе  ",
            "education": "  Образование  ",
            "services": "  Услуги  ",
            "reviews": "  Отзывы  ",
        }
    )

    put_response = client.put("/api/specialist/profile", json=payload, cookies=cookies)
    assert put_response.status_code == 200
    body = put_response.json()
    assert isinstance(body["public_slug"], str)
    assert _PRIVATE_SLUG_RE.fullmatch(body["public_slug"]) is not None
    assert body["is_published"] is False
    assert {k: v for k, v in body.items() if k not in {"public_slug", "is_published"}} == {
        "first_name": "Анна",
        "middle_name": "Сергеевна",
        "last_name": "Петрова",
        "specialization": "Психолог",
        "hero_quote": "С заботой",
        "about": "О себе",
        "education": "Образование",
        "services": "Услуги",
        "reviews": "Отзывы",
    }

    async def _assert_profile_name_and_specialization_saved():
        async with database.async_session_factory() as session:
            profile = (
                await session.execute(
                    text(
                        "SELECT display_name, first_name, middle_name, last_name, specialization "
                        "FROM specialist_public_profile WHERE specialist_id = :sid"
                    ),
                    {"sid": str(specialist_id)},
                )
            ).mappings().first()
            assert profile is not None
            assert profile["display_name"] == "Анна Сергеевна Петрова"
            assert profile["first_name"] == "Анна"
            assert profile["middle_name"] == "Сергеевна"
            assert profile["last_name"] == "Петрова"
            assert profile["specialization"] == "Психолог"

    asyncio.run(_assert_profile_name_and_specialization_saved())


def test_second_put_keeps_same_slug(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    cookies = {web_server.config.WEB_CONNECT_COOKIE_NAME: cookie}

    payload = _valid_profile_payload()
    first_response = client.put("/api/specialist/profile", json=payload, cookies=cookies)
    assert first_response.status_code == 200
    first_slug = first_response.json()["public_slug"]
    assert isinstance(first_slug, str)

    payload["hero_quote"] = "Обновлённая цитата"
    second_response = client.put("/api/specialist/profile", json=payload, cookies=cookies)
    assert second_response.status_code == 200
    assert second_response.json()["public_slug"] == first_slug


def test_slug_collision_picks_next_suffix(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    target_specialist_id = asyncio.run(_prepare_specialist(database))
    occupied_specialist_id = uuid.uuid4()

    async def _seed_occupied_slug():
        async with database.async_session_factory() as session:
            session.add(database.Specialist(specialist_id=occupied_specialist_id, status=database.SpecialistStatus.onboarding, specialization="Психолог"))
            await session.execute(
                text(
                    """
                    INSERT INTO specialist_public_profile (
                        id, specialist_id, public_slug, display_name, first_name, middle_name, last_name,
                        specialization, hero_quote, contact_telegram, contact_whatsapp, contact_phone, contact_email,
                        client_bot_username, is_published, created_at, updated_at
                    ) VALUES (
                        :id, :specialist_id, :public_slug, :display_name, :first_name, :middle_name, :last_name,
                        :specialization, :hero_quote, :contact_telegram, :contact_whatsapp, :contact_phone, :contact_email,
                        :client_bot_username, :is_published, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "specialist_id": str(occupied_specialist_id),
                    "public_slug": "annapetrova_10",
                    "display_name": "Анна Петрова",
                    "first_name": "Анна",
                    "middle_name": None,
                    "last_name": "Петрова",
                    "specialization": "Психолог",
                    "hero_quote": "",
                    "contact_telegram": None,
                    "contact_whatsapp": None,
                    "contact_phone": None,
                    "contact_email": None,
                    "client_bot_username": "",
                    "is_published": False,
                },
            )
            await session.commit()

    asyncio.run(_seed_occupied_slug())

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(target_specialist_id, 777)
    response = client.put("/api/specialist/profile", json=_valid_profile_payload(), cookies={web_server.config.WEB_CONNECT_COOKIE_NAME: cookie})

    assert response.status_code == 200
    assert response.json()["public_slug"] == "annapetrova_11"


def test_slug_generation_failure_returns_409(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    async def _seed_all_suffixes_taken():
        async with database.async_session_factory() as session:
            for suffix in range(10, 31):
                sid = uuid.uuid4()
                session.add(database.Specialist(specialist_id=sid, status=database.SpecialistStatus.onboarding, specialization="Психолог"))
                await session.execute(
                    text(
                        """
                        INSERT INTO specialist_public_profile (
                            id, specialist_id, public_slug, display_name, first_name, middle_name, last_name,
                            specialization, hero_quote, contact_telegram, contact_whatsapp, contact_phone, contact_email,
                            client_bot_username, is_published, created_at, updated_at
                        ) VALUES (
                            :id, :specialist_id, :public_slug, :display_name, :first_name, :middle_name, :last_name,
                            :specialization, :hero_quote, :contact_telegram, :contact_whatsapp, :contact_phone, :contact_email,
                            :client_bot_username, :is_published, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "specialist_id": str(sid),
                        "public_slug": f"annapetrova_{suffix:02d}",
                        "display_name": "Анна Петрова",
                        "first_name": "Анна",
                        "middle_name": None,
                        "last_name": "Петрова",
                        "specialization": "Психолог",
                        "hero_quote": "",
                        "contact_telegram": None,
                        "contact_whatsapp": None,
                        "contact_phone": None,
                        "contact_email": None,
                        "client_bot_username": "",
                        "is_published": False,
                    },
                )
            await session.commit()

    asyncio.run(_seed_all_suffixes_taken())

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    response = client.put("/api/specialist/profile", json=_valid_profile_payload(), cookies={web_server.config.WEB_CONNECT_COOKIE_NAME: cookie})

    assert response.status_code == 409
    assert response.json() == {"detail": "slug_generation_failed"}


def test_publish_requires_cookie(tmp_path, monkeypatch):
    web_server, _database = _load_web_app(tmp_path, monkeypatch)
    client = TestClient(web_server.app)

    response = client.post("/api/specialist/profile/publish")

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_publish_sets_is_published_true(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    cookies = {web_server.config.WEB_CONNECT_COOKIE_NAME: cookie}

    async def _seed_slug():
        async with database.async_session_factory() as session:
            await session.execute(
                text("UPDATE specialist_public_profile SET public_slug = :slug WHERE specialist_id = :sid"),
                {"slug": "anna-petrova", "sid": str(specialist_id)},
            )
            await session.commit()

    client.get("/api/specialist/profile", cookies=cookies)
    asyncio.run(_seed_slug())

    response = client.post("/api/specialist/profile/publish", cookies=cookies)

    assert response.status_code == 200
    assert response.json() == {"ok": True, "is_published": True}

    async def _assert_published():
        async with database.async_session_factory() as session:
            row = (
                await session.execute(
                    text("SELECT is_published FROM specialist_public_profile WHERE specialist_id = :sid"),
                    {"sid": str(specialist_id)},
                )
            ).mappings().first()
            assert row is not None
            assert row["is_published"] in (True, 1)

    asyncio.run(_assert_published())


def test_start_subscription_payment_requires_cookie(tmp_path, monkeypatch):
    web_server, _database = _load_web_app(tmp_path, monkeypatch)
    client = TestClient(web_server.app)

    response = client.post(
        "/api/specialist/profile/billing/subscription-payment",
        json={"tariff_code": "pro-monthly", "return_url": "/billing/return"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_start_subscription_payment_returns_pending_confirmation_url_without_activation(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    import backend.api.specialist_profile_private as specialist_profile_private_api

    async def _fake_start_specialist_subscription_payment(*, specialist_id, tariff_code, return_url):
        assert tariff_code == "pro-monthly"
        assert return_url == "http://localhost/billing/return"
        return types.SimpleNamespace(
            payment_id=uuid.uuid4(),
            status=database.BillingPaymentStatus.pending,
            confirmation_url="https://pay.example/confirm",
        )

    monkeypatch.setattr(
        specialist_profile_private_api,
        "start_specialist_subscription_payment",
        _fake_start_specialist_subscription_payment,
    )

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    response = client.post(
        "/api/specialist/profile/billing/subscription-payment",
        json={"tariff_code": "pro-monthly", "return_url": "/billing/return"},
        cookies={web_server.config.WEB_CONNECT_COOKIE_NAME: cookie},
    )

    assert response.status_code == 200
    assert response.json()["tariff_code"] == "pro-monthly"
    assert response.json()["payment_status"] == "pending"
    assert response.json()["requires_redirect"] is True
    assert response.json()["confirmation_url"] == "https://pay.example/confirm"

    async def _assert_no_subscription_activation():
        async with database.async_session_factory() as session:
            subscription = (
                await session.execute(
                    text("SELECT status FROM billing_subscriptions WHERE specialist_id = :sid"),
                    {"sid": str(specialist_id)},
                )
            ).mappings().first()
            assert subscription is None

    asyncio.run(_assert_no_subscription_activation())


def test_start_subscription_payment_rejects_inactive_tariff(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    import backend.api.specialist_profile_private as specialist_profile_private_api

    async def _fake_start_specialist_subscription_payment(**_kwargs):
        raise specialist_profile_private_api.BillingError("tariff_inactive")

    monkeypatch.setattr(
        specialist_profile_private_api,
        "start_specialist_subscription_payment",
        _fake_start_specialist_subscription_payment,
    )

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    response = client.post(
        "/api/specialist/profile/billing/subscription-payment",
        json={"tariff_code": "pro-monthly", "return_url": "/billing/return"},
        cookies={web_server.config.WEB_CONNECT_COOKIE_NAME: cookie},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "tariff_inactive"}


def test_unpublish_sets_is_published_false(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    cookies = {web_server.config.WEB_CONNECT_COOKIE_NAME: cookie}

    client.get("/api/specialist/profile", cookies=cookies)

    async def _seed_published():
        async with database.async_session_factory() as session:
            await session.execute(
                text(
                    "UPDATE specialist_public_profile "
                    "SET public_slug = :slug, is_published = :published WHERE specialist_id = :sid"
                ),
                {"slug": "anna-petrova", "published": True, "sid": str(specialist_id)},
            )
            await session.commit()

    asyncio.run(_seed_published())

    response = client.post("/api/specialist/profile/unpublish", cookies=cookies)

    assert response.status_code == 200
    assert response.json() == {"ok": True, "is_published": False}

    async def _assert_unpublished():
        async with database.async_session_factory() as session:
            row = (
                await session.execute(
                    text("SELECT is_published FROM specialist_public_profile WHERE specialist_id = :sid"),
                    {"sid": str(specialist_id)},
                )
            ).mappings().first()
            assert row is not None
            assert row["is_published"] in (False, 0)

    asyncio.run(_assert_unpublished())


def test_publish_without_slug_returns_422_slug_missing(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    cookies = {web_server.config.WEB_CONNECT_COOKIE_NAME: cookie}

    client.get("/api/specialist/profile", cookies=cookies)

    response = client.post("/api/specialist/profile/publish", cookies=cookies)

    assert response.status_code == 422
    assert response.json() == {"detail": "slug_missing"}


def test_get_returns_public_slug_and_is_published_fields(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    cookies = {web_server.config.WEB_CONNECT_COOKIE_NAME: cookie}

    client.get("/api/specialist/profile", cookies=cookies)

    async def _seed_profile_flags():
        async with database.async_session_factory() as session:
            await session.execute(
                text(
                    "UPDATE specialist_public_profile "
                    "SET public_slug = :slug, is_published = :published WHERE specialist_id = :sid"
                ),
                {"slug": "ivan-ivanov", "published": True, "sid": str(specialist_id)},
            )
            await session.commit()

    asyncio.run(_seed_profile_flags())

    response = client.get("/api/specialist/profile", cookies=cookies)

    assert response.status_code == 200
    assert response.json()["public_slug"] == "ivan-ivanov"
    assert response.json()["is_published"] is True
