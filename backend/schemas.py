from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

DEFAULT_TENANT: Optional[str] = None


class SourceEnum(str, Enum):
    firewall = "firewall"
    crowdstrike = "crowdstrike"
    aws = "aws"
    m365 = "m365"
    ad = "ad"
    api = "api"
    network = "network"


class ActionEnum(str, Enum):
    allow = "allow"
    deny = "deny"
    create = "create"
    delete = "delete"
    login = "login"
    logout = "logout"
    alert = "alert"


class SingleIngestRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
        json_schema_extra={
            "example": {
                "tenant": "demoB",
                "source": "aws",
                "cloud": {
                    "service": "iam",
                    "account_id": "123456789012",
                    "region": "ap-southeast-1",
                },
                "event_type": "CreateUser",
                "user": "admin",
                "@timestamp": "2025-08-20T09:10:00Z",
                "raw": {
                    "eventName": "CreateUser",
                    "requestParameters": {"userName": "temp-user"},
                },
            }
        },
    )

    tenant: Optional[str] = None
    source: Optional[SourceEnum] = None
    timestamp: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("@timestamp", "timestamp", "time"),
        serialization_alias="@timestamp",
    )

    vendor: Optional[str] = None
    product: Optional[str] = None
    event_type: Optional[str] = None
    event_subtype: Optional[str] = None
    severity: Optional[int] = None
    action: Optional[str] = None

    ip: Optional[str] = None
    src_ip: Optional[str] = None
    src_port: Optional[int] = None
    dst_ip: Optional[str] = None
    dst_port: Optional[int] = None
    protocol: Optional[str] = None

    user: Optional[str] = None
    host: Optional[str] = None
    process: Optional[str] = None
    url: Optional[str] = None
    http_method: Optional[str] = None
    status_code: Optional[int] = None
    status: Optional[str] = None
    workload: Optional[str] = None
    rule_name: Optional[str] = None
    rule_id: Optional[str] = None

    reason: Optional[str] = None
    sha256: Optional[str] = None
    file_hash_sha256: Optional[str] = Field(default=None, alias="file.hash.sha256")

    cloud: Optional[Dict[str, Any]] = None
    cloud_account_id: Optional[str] = Field(default=None, alias="cloud.account_id")
    cloud_region: Optional[str] = Field(default=None, alias="cloud.region")
    cloud_service: Optional[str] = Field(default=None, alias="cloud.service")

    raw: Optional[Any] = None
    tags: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("_tags", "tags"),
        serialization_alias="_tags",
    )

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return [x.strip() for x in value.split(",") if x.strip()]
        if isinstance(value, (tuple, set)):
            return [str(x).strip() for x in value if str(x).strip()]
        return value


class NormalizedLog(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    timestamp: str = Field(..., alias="@timestamp")
    tenant: Optional[str] = None
    source: SourceEnum

    vendor: Optional[str] = None
    product: Optional[str] = None
    event_type: Optional[str] = None
    event_subtype: Optional[str] = None
    severity: Optional[int] = Field(default=None, ge=0, le=10)
    action: Optional[ActionEnum] = None

    src_ip: Optional[str] = None
    src_port: Optional[int] = Field(default=None, ge=0, le=65535)
    dst_ip: Optional[str] = None
    dst_port: Optional[int] = Field(default=None, ge=0, le=65535)
    protocol: Optional[str] = None

    user: Optional[str] = None
    host: Optional[str] = None
    process: Optional[str] = None
    url: Optional[str] = None
    http_method: Optional[str] = None
    status_code: Optional[int] = None
    status: Optional[str] = None
    workload: Optional[str] = None
    rule_name: Optional[str] = None
    rule_id: Optional[str] = None

    reason: Optional[str] = None
    logon_type: Optional[int] = None
    interface: Optional[str] = None
    mac_address: Optional[str] = None

    file_hash_sha256: Optional[str] = Field(default=None, alias="file.hash.sha256")

    cloud_account_id: Optional[str] = Field(default=None, alias="cloud.account_id")
    cloud_region: Optional[str] = Field(default=None, alias="cloud.region")
    cloud_service: Optional[str] = Field(default=None, alias="cloud.service")

    raw: Optional[Any] = None
    tags: Optional[List[str]] = Field(default=None, alias="_tags")

    @field_validator("protocol")
    @classmethod
    def normalize_protocol(cls, value: Optional[str]) -> Optional[str]:
        return value.lower() if isinstance(value, str) else value

    @field_validator("http_method")
    @classmethod
    def normalize_http_method(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if isinstance(value, str) else value

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return [x.strip() for x in value.split(",") if x.strip()]
        return value
