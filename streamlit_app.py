import streamlit as st

from agents.finance_agent import FinanceAgent

st.set_page_config(
    page_title="Finance AI",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Finance AI Assistant for state street")
st.caption("Ask questions about publicly traded companies.")


# Maps the radio label to the provider mode.
DATA_SOURCE_MODES = {
    "Auto (Databricks → Yahoo)": "auto",
    "Databricks Unity Catalog": "databricks",
    "Yahoo Finance": "yahoo",
}


def format_source_badge(summary: dict):
    """
    Build a human-readable badge showing which backend(s) served the answer.
    Returns None when no data tool was called.
    """

    log = summary.get("log", [])
    if not log:
        return None

    databricks = sorted({str(s) for s in summary.get("databricks", []) if s})
    yahoo = sorted({str(s) for s in summary.get("yahoo", []) if s})

    parts = []
    if databricks:
        parts.append(f"🟢 Databricks: {', '.join(databricks)}")
    if yahoo:
        parts.append(f"🟡 Yahoo Finance: {', '.join(yahoo)}")

    # Group misses by which backend was actually queried, so the badge names
    # the source even when nothing was found.
    attempted_label = {
        "databricks": "Databricks",
        "yahoo": "Yahoo Finance",
        "databricks+yahoo": "Databricks + Yahoo",
    }
    misses = {}
    for entry in summary.get("not_found", []):
        symbol = str(entry.get("symbol") or "")
        if symbol:
            misses.setdefault(entry.get("attempted"), set()).add(symbol)

    for attempted, symbols in misses.items():
        source_name = attempted_label.get(attempted, attempted)
        parts.append(
            f"⚠️ Not found in {source_name}: {', '.join(sorted(symbols))}"
        )

    if not parts:
        return None

    return "Data source — " + "  ·  ".join(parts)

# Create agent only once
if "agent" not in st.session_state:
    st.session_state.agent = FinanceAgent()

# Store chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:

    st.header("Finance AI")

    # Data Source Selection
    data_source = st.radio(
        "Data Source",
        list(DATA_SOURCE_MODES.keys()),
        index=0,
        help=(
            "Auto tries Databricks first and falls back to Yahoo. Each "
            "answer shows which source actually served the data."
        ),
    )

    st.session_state["data_source"] = data_source

    st.divider()

    if st.button("🗑 Clear Chat"):

        st.session_state.messages = []
        st.session_state.agent.clear_history()

        st.rerun()

# Display previous messages
for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message.get("source"):
            st.caption(message["source"])

# Chat input
if prompt := st.chat_input("Ask a financial question..."):

    # Display user message
    st.chat_message("user").markdown(prompt)

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    # Honor the selected data source before asking.
    st.session_state.agent.set_data_source(
        DATA_SOURCE_MODES[st.session_state["data_source"]]
    )

    with st.spinner("Analyzing..."):

        response = st.session_state.agent.ask(prompt)

    badge = format_source_badge(
        st.session_state.agent.get_last_sources()
    )

    with st.chat_message("assistant"):
        st.markdown(response)
        if badge:
            st.caption(badge)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response,
            "source": badge,
        }
    )