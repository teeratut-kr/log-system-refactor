import pandas as pd
import streamlit as st

try:
    from frontend.api import fetch_alerts
    from frontend.components import build_rank_chart, format_alerts_table, top_counts
except ModuleNotFoundError:
    from api import fetch_alerts
    from components import build_rank_chart, format_alerts_table, top_counts


def render_alerts_page(api_base: str, base_params: dict, selected_user: str) -> None:
    alert_params = {
        "threshold": 3,
        "window_minutes": 5,
        "limit": 100,
    }
    if base_params.get("tenant"):
        alert_params["tenant"] = base_params["tenant"]
    if base_params.get("start"):
        alert_params["start"] = base_params["start"]
    if base_params.get("end"):
        alert_params["end"] = base_params["end"]

    try:
        payload = fetch_alerts(api_base, alert_params, selected_user)
        items = payload.get("items", [])
        count = payload.get("count", 0)
    except Exception as exc:
        st.error(f"Failed to load alerts from backend: {exc}")
        return

    st.markdown(
        """
        <div class="section-card">
            <strong>Alert rule</strong><br>
            <span class="small-muted">Repeated failed logins from the same IP within 5 minutes (threshold = 3).</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Total alerts", f"{count:,}")
    c2.metric("Affected IPs", f"{len({str(x.get('src_ip')) for x in items if x.get('src_ip')}):,}")
    c3.metric("Sample events", f"{sum(len(x.get('sample_events') or []) for x in items):,}")

    if not items:
        st.success("No alerts were triggered for the current filters.")
        return

    top_col, detail_col = st.columns([1, 1.2])
    with top_col:
        build_rank_chart(top_counts(pd.DataFrame(items), "src_ip"), "src_ip", "Alerted IPs", "No IP data.", height=320)

    with detail_col:
        st.subheader("Alert list")
        st.dataframe(format_alerts_table(items), use_container_width=True, height=320)

    st.subheader("Alert details")
    for idx, alert in enumerate(items, start=1):
        title = f"{idx}. {alert.get('src_ip', '-')} • {alert.get('match_count', 0)} failed logins"
        with st.expander(title):
            st.write(alert.get("description", "-"))
            c1, c2 = st.columns(2)
            c1.write(f"First seen: {alert.get('first_seen', '-')}")
            c2.write(f"Last seen: {alert.get('last_seen', '-')}")
            st.write(f"Users: {', '.join(alert.get('users') or []) or '-'}")
            st.write(f"Tenants: {', '.join(alert.get('tenants') or []) or '-'}")
            sample_df = pd.DataFrame(alert.get("sample_events") or [])
            if not sample_df.empty:
                st.dataframe(sample_df.fillna("-"), use_container_width=True)
