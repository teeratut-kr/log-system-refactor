import json
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

try:
    from frontend.config import RAW_PREVIEW_MAX_LEN
except ModuleNotFoundError:
    from config import RAW_PREVIEW_MAX_LEN


def format_raw_for_display(value: Any, max_len: int = RAW_PREVIEW_MAX_LEN) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"

    if isinstance(value, dict):
        if "message" in value and value["message"] is not None:
            text = str(value["message"])
        else:
            text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)

    return text[:max_len] + "..." if len(text) > max_len else text


def format_logs_table(df: pd.DataFrame) -> pd.DataFrame:
    desired_columns = [
        "@timestamp",
        "tenant",
        "source",
        "event_type",
        "severity",
        "src_ip",
        "dst_ip",
        "user",
        "action",
        "raw",
    ]

    table_df = df.copy()
    for col in desired_columns:
        if col not in table_df.columns:
            table_df[col] = None

    table_df = table_df[desired_columns].sort_values(by="@timestamp", ascending=False, na_position="last")
    display_df = table_df.copy()

    if "raw" in display_df.columns:
        display_df["raw"] = table_df["raw"].apply(lambda x: format_raw_for_display(x, max_len=RAW_PREVIEW_MAX_LEN))

    if "@timestamp" in display_df.columns:
        ts = pd.to_datetime(display_df["@timestamp"], errors="coerce", utc=True)
        display_df["@timestamp"] = ts.dt.strftime("%Y-%m-%d %H:%M:%S UTC").fillna("-")

    if "severity" in display_df.columns:
        sev = pd.to_numeric(display_df["severity"], errors="coerce")
        display_df["severity"] = sev.apply(lambda x: "-" if pd.isna(x) else str(int(x)))

    return display_df.fillna("-")


def format_alerts_table(alerts: List[Dict[str, Any]]) -> pd.DataFrame:
    if not alerts:
        return pd.DataFrame(
            columns=["last_seen", "src_ip", "match_count", "users", "tenants", "event_types", "description"]
        )

    rows: List[Dict[str, Any]] = []
    for alert in alerts:
        rows.append(
            {
                "last_seen": alert.get("last_seen", "-"),
                "src_ip": alert.get("src_ip", "-"),
                "match_count": alert.get("match_count", 0),
                "users": ", ".join(alert.get("users") or []) or "-",
                "tenants": ", ".join(alert.get("tenants") or []) or "-",
                "event_types": ", ".join(alert.get("event_types") or []) or "-",
                "description": alert.get("description", "-"),
            }
        )
    return pd.DataFrame(rows)


def render_export_actions(df: pd.DataFrame) -> None:
    export_df = format_logs_table(df)
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    c1, c2 = st.columns([1, 2.2])
    with c1:
        st.download_button(
            "Download visible rows (CSV)",
            data=csv_bytes,
            file_name="visible_logs.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with c2:
        st.caption("Export only includes rows currently visible under the active filters.")
