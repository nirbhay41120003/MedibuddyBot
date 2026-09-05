import os
import uuid

import requests
import streamlit as st

st.set_page_config(page_title="Weather Advisory Bot", page_icon="⛅")
st.title("Weather Advisory Support Bot")
st.caption("Live weather, policy-bound answers. Include a city on the first message.")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "context_location" not in st.session_state:
    st.session_state.context_location = None
if "context_intent" not in st.session_state:
    st.session_state.context_intent = None

for item in st.session_state.messages:
    with st.chat_message(item["role"]):
        st.write(item["content"])

if prompt := st.chat_input("e.g. Is it safe to cycle in Bhopal today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        try:
            base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
            response = requests.post(f"{base_url}/chat", json={
                "session_id": st.session_state.session_id,
                "message": prompt,
                "context_location": st.session_state.context_location,
                "context_intent": st.session_state.context_intent,
            }, timeout=20)
            response.raise_for_status()
            payload = response.json()
            answer = payload["reply"]
            # Keep only backend-returned structured context, never inferred
            # advice or weather, so a server reload does not lose a follow-up.
            st.session_state.context_location = payload.get("context_location")
            st.session_state.context_intent = payload.get("context_intent")
        except requests.RequestException:
            answer = "The backend is unavailable. Start it with `uvicorn app.main:app --reload`."
        st.write(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
