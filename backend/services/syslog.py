import asyncio
from typing import Any

from ..logging_config import get_logger
from ..normalizer import normalize_log
from ..parsers import parse_syslog_line
from ..storage.base import Storage

logger = get_logger(__name__)


class SyslogUDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def datagram_received(self, data: bytes, addr: Any) -> None:
        text = data.decode("utf-8", errors="replace").strip()
        if not text:
            return
        asyncio.create_task(self._handle_message(text, addr))

    async def _handle_message(self, text: str, addr: Any) -> None:
        try:
            source_hint = "firewall" if "vendor=" in text or "policy=" in text else "network"
            raw_item = parse_syslog_line(text, source_hint=source_hint)
            normalized = normalize_log(raw_item, default_source=source_hint)
            await self.storage.save_log(normalized)
            logger.debug("UDP syslog message ingested from %s", addr)
        except Exception:
            logger.exception("UDP syslog parse error from %s", addr)
