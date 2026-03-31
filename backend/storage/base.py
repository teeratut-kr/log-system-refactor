from typing import Any, Dict, Optional, Protocol


class Storage(Protocol):
    async def startup(self) -> None: ...

    async def shutdown(self) -> None: ...

    async def save_log(self, item: Dict[str, Any]) -> Dict[str, Any]: ...

    async def query_logs(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        tenant: Optional[str] = None,
        source: Optional[str] = None,
        action: Optional[str] = None,
        min_severity: Optional[int] = None,
        max_severity: Optional[int] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        q: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def query_alerts(
        self,
        *,
        tenant: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        threshold: int = 3,
        window_minutes: int = 5,
        limit: int = 100,
    ) -> Dict[str, Any]: ...

    async def run_retention(self, *, retention_days: Optional[int] = None) -> Dict[str, Any]: ...

    async def get_retention_status(self) -> Dict[str, Any]: ...

    @property
    def backend_name(self) -> str: ...
