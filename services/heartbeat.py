import asyncio
import logging
import time

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SEC = 5.0
LAST_TICK_TS = time.monotonic()


async def heartbeat_task() -> None:
    logger.info("heartbeat_task started")
    try:
        while True:
            global LAST_TICK_TS
            LAST_TICK_TS = time.monotonic()
            await asyncio.sleep(HEARTBEAT_INTERVAL_SEC)
    except asyncio.CancelledError:
        logger.info("heartbeat_task stopped")
        raise
