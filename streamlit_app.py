import streamlit as st

from agents.finance_agent import FinanceAgent

st.set_page_config(
    page_title="Finance AI",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Finance AI Assistant")
st.caption("Ask questions about publicly traded companies.")

# Create agent only once
if "agent" not in st.session_state:
    st.session_state.agent = FinanceAgent()

# Store chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])

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

    with st.spinner("Analyzing..."):

        response = st.session_state.agent.ask(prompt)

    st.chat_message("assistant").markdown(response)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response
        }
    )

# Sidebar
with st.sidebar:

    st.header("Finance AI")

    if st.button("🗑 Clear Chat"):

        st.session_state.messages = []
        st.session_state.agent.clear_history()

        st.rerun()