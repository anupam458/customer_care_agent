import streamlit as st
import database
import agent

# --- Init ---
if "initialized" not in st.session_state:
    database.init_db()
    st.session_state.initialized = True

st.set_page_config(page_title="Support Agent", page_icon="🎧", layout="wide")

# --- Sidebar ---
st.sidebar.title("🎧 Support Agent")
st.sidebar.markdown("Powered by **CockroachDB** + **Gemini**")
st.sidebar.divider()

customer_id = st.sidebar.text_input(
    "Customer ID",
    value="CUST-001",
    help="Each customer ID gets its own persistent memory."
)

if st.sidebar.button("🗑️ Clear Memory"):
    import psycopg2
    from dotenv import load_dotenv
    import os
    load_dotenv()
    conn = psycopg2.connect(os.getenv("COCKROACH_URI"))
    cur = conn.cursor()
    cur.execute("DELETE FROM support_memories WHERE customer_id = %s", (customer_id,))
    conn.commit()
    cur.close()
    conn.close()
    st.sidebar.success("Memory cleared!")
    st.rerun()

# --- Main ---
st.title("🎧 Customer Support Agent")
st.caption("Agentic memory powered by CockroachDB Serverless + Google Gemini")

# Chat history in session
if "messages" not in st.session_state:
    st.session_state.messages = []

# Load previous history from DB
if "loaded" not in st.session_state or st.session_state.loaded_customer != customer_id:
    history = database.get_history(customer_id, limit=50)
    st.session_state.messages = [
        {"role": h["role"], "content": h["content"]} for h in history
    ]
    st.session_state.loaded_customer = customer_id

# Display messages
for msg in st.session_state.messages:
    with st.chat_message("user" if msg["role"] == "user" else "assistant"):
        st.markdown(msg["content"])

# Input
if prompt := st.chat_input("Type your message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                reply, memories = agent.process_message(customer_id, prompt)
            except Exception as e:
                reply = f"⚠️ Error: {str(e)}"
                memories = []
        st.markdown(reply)

    st.session_state.messages.append({"role": "agent", "content": reply})

# --- Memory Panel ---
st.divider()
st.subheader("🧠 Agent Memory (CockroachDB)")
history = database.get_history(customer_id, limit=10)
if history:
    for h in reversed(history):
        icon = "👤" if h["role"] == "user" else "🤖"
        st.text(f"{icon} [{h['role']}] {h['content'][:120]}")
else:
    st.info("No memories yet. Start chatting!")