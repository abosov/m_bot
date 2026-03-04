import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from database import AdminAuditLog, Base
from services.admin_audit import write_admin_audit_log

pytest.importorskip("aiosqlite")


@pytest.mark.asyncio
async def test_write_admin_audit_log_inserts_and_reads_back(tmp_path):
    db_path = tmp_path / "admin_audit_helper.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    target_id = uuid.uuid4()

    async with session_factory() as session:
        await write_admin_audit_log(
            session,
            request_id="req-1",
            admin_subject="cookie_session",
            action="disable_specialist",
            target_type="specialist",
            target_id=target_id,
            success=True,
            payload={
                "old_status": "active",
                "new_status": "disabled",
                "access_token": "should-not-be-stored",
            },
            error_code=None,
            error_message="token leaked",
        )
        await session.commit()

        row = (await session.execute(select(AdminAuditLog))).scalar_one()
        assert row.request_id == "req-1"
        assert row.admin_subject == "cookie_session"
        assert row.action == "disable_specialist"
        assert row.target_type == "specialist"
        assert row.target_id == target_id
        assert row.success is True
        assert row.payload_json["old_status"] == "active"
        assert row.payload_json["new_status"] == "disabled"
        assert row.payload_json["access_token"] == "[redacted]"
        assert row.error_message == "[redacted]"

    await engine.dispose()


@pytest.mark.asyncio
async def test_write_admin_audit_log_never_raises_on_insert_failure(tmp_path, caplog):
    db_path = tmp_path / "admin_audit_helper_fail.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    target_id = uuid.uuid4()

    async with session_factory() as session:
        await write_admin_audit_log(
            session,
            request_id="req-2",
            admin_subject="cookie_session",
            action="enable_specialist",
            target_type="specialist",
            target_id=target_id,
            success=False,
            payload={"old_status": "disabled", "new_status": "active"},
            error_code="db_write_failed",
            error_message="insert failed",
        )

    assert "event=admin_audit_log_failed" in caplog.text
    await engine.dispose()
