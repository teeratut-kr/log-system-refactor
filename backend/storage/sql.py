CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS logs (
    id BIGSERIAL PRIMARY KEY,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_time TIMESTAMPTZ NOT NULL,
    tenant TEXT,
    source TEXT NOT NULL,
    vendor TEXT,
    product TEXT,
    event_type TEXT,
    event_subtype TEXT,
    severity INTEGER,
    action TEXT,
    src_ip TEXT,
    src_port INTEGER,
    dst_ip TEXT,
    dst_port INTEGER,
    protocol TEXT,
    user_name TEXT,
    host TEXT,
    process TEXT,
    url TEXT,
    http_method TEXT,
    status_code INTEGER,
    status TEXT,
    workload TEXT,
    rule_name TEXT,
    rule_id TEXT,
    reason TEXT,
    logon_type INTEGER,
    interface TEXT,
    mac_address TEXT,
    file_hash_sha256 TEXT,
    cloud_account_id TEXT,
    cloud_region TEXT,
    cloud_service TEXT,
    raw TEXT,
    tags TEXT[],
    document JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_logs_event_time_desc ON logs (event_time DESC);
CREATE INDEX IF NOT EXISTS idx_logs_tenant ON logs (tenant);
CREATE INDEX IF NOT EXISTS idx_logs_source ON logs (source);
CREATE INDEX IF NOT EXISTS idx_logs_action ON logs (action);
CREATE INDEX IF NOT EXISTS idx_logs_severity ON logs (severity);
CREATE INDEX IF NOT EXISTS idx_logs_tags_gin ON logs USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_logs_document_gin ON logs USING GIN (document);
"""

ALLOW_NULL_TENANT_SQL = "ALTER TABLE logs ALTER COLUMN tenant DROP NOT NULL;"
