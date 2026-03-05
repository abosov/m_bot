from __future__ import annotations

import asyncio
import os

from backend.tests.fixtures.public_specialist_seed import seed_public_specialist_tsareva_e12


async def _run() -> None:
    app_env = os.getenv("APP_ENV", "").lower()
    if app_env != "dev":
        raise SystemExit("Refusing to run: APP_ENV must be 'dev'.")

    from database import async_session_factory

    async with async_session_factory() as session:
        await seed_public_specialist_tsareva_e12(session)
        await session.commit()

    print("Seeded public specialist example: TsarevaE_12")


if __name__ == "__main__":
    asyncio.run(_run())
