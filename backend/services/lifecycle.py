import asyncio
from fastapi import FastAPI

from ..config import RETENTION_CLEANUP_INTERVAL_MINUTES, RETENTION_DAYS, SYSLOG_UDP_HOST, SYSLOG_UDP_PORT
from ..storage.factory import create_storage
from .syslog import SyslogUDPProtocol


async def retention_worker(app: FastAPI) -> None:
    while True:
        try:
            await asyncio.sleep(max(1, RETENTION_CLEANUP_INTERVAL_MINUTES) * 60)
            storage = getattr(app.state, "storage", None)
            if storage:
                result = await storage.run_retention(retention_days=RETENTION_DAYS)
                print(f"[retention] cleanup completed: {result}")
        except asyncio.CancelledError:
            break
        except Exception as exc:
            print(f"[retention] cleanup error: {exc}")


async def on_startup(app: FastAPI) -> None:
    storage = create_storage()
    await storage.startup()
    app.state.storage = storage

    startup_retention_result = await storage.run_retention(retention_days=RETENTION_DAYS)
    app.state.last_retention_result = startup_retention_result

    try:
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: SyslogUDPProtocol(app.state.storage),
            local_addr=(SYSLOG_UDP_HOST, SYSLOG_UDP_PORT),
        )
        app.state.syslog_transport = transport
    except Exception as exc:
        print(f"Failed to start UDP syslog listener: {exc}")

    app.state.retention_task = asyncio.create_task(retention_worker(app))


async def on_shutdown(app: FastAPI) -> None:
    transport = getattr(app.state, "syslog_transport", None)
    if transport:
        transport.close()

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
