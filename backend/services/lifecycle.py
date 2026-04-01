import asyncio
from fastapi import FastAPI

from ..config import RETENTION_CLEANUP_INTERVAL_MINUTES, RETENTION_DAYS, SYSLOG_UDP_HOST, SYSLOG_UDP_PORT
from ..logging_config import get_logger
from ..storage.factory import create_storage
from .syslog import SyslogUDPProtocol

logger = get_logger(__name__)


async def retention_worker(app: FastAPI) -> None:
    interval_seconds = max(1, RETENTION_CLEANUP_INTERVAL_MINUTES) * 60
    logger.info("Retention worker started", extra={"interval_seconds": interval_seconds})
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            storage = getattr(app.state, "storage", None)
            if storage:
                result = await storage.run_retention(retention_days=RETENTION_DAYS)
                logger.info("Retention cleanup completed: %s", result)
        except asyncio.CancelledError:
            logger.info("Retention worker stopped")
            break
        except Exception:
            logger.exception("Retention cleanup failed")


async def on_startup(app: FastAPI) -> None:
    storage = create_storage()
    await storage.startup()
    app.state.storage = storage
    logger.info("Storage started with backend=%s", storage.backend_name)

    startup_retention_result = await storage.run_retention(retention_days=RETENTION_DAYS)
    app.state.last_retention_result = startup_retention_result
    logger.info("Startup retention completed: %s", startup_retention_result)

    try:
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: SyslogUDPProtocol(app.state.storage),
            local_addr=(SYSLOG_UDP_HOST, SYSLOG_UDP_PORT),
        )
        app.state.syslog_transport = transport
        logger.info("UDP syslog listener started on %s:%s", SYSLOG_UDP_HOST, SYSLOG_UDP_PORT)
    except Exception:
        logger.exception("Failed to start UDP syslog listener")

    app.state.retention_task = asyncio.create_task(retention_worker(app))


async def on_shutdown(app: FastAPI) -> None:
    transport = getattr(app.state, "syslog_transport", None)
    if transport:
        transport.close()
        logger.info("UDP syslog listener stopped")

    retention_task = getattr(app.state, "retention_task", None)
    if retention_task:
        retention_task.cancel()
        try:
            await retention_task
        except asyncio.CancelledError:
            pass

    storage = getattr(app.state, "storage", None)
    if storage:
        await storage.shutdown()
        logger.info("Storage shutdown completed")
