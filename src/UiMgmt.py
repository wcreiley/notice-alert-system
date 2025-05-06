import os

import requests
import streamlit as st
from dotenv import load_dotenv


# UI to allow human interaction with the LLM Engine
#   This is based on https://github.com/pathwaycom/llm-app/tree/main/examples/pipelines/drive_alert
class UiMgmt:

    def __init__(self):
        load_dotenv()
        self.api_host = os.environ.get("PATHWAY_REST_CONNECTOR_HOST", "127.0.0.1")
        self.api_port = int(os.environ.get("PATHWAY_REST_CONNECTOR_PORT", 8080))
        self.url = f"http://{self.api_host}:{self.api_port}/"

        if "messages" not in st.session_state:
            st.session_state.messages = []

    def run(self):

        with st.sidebar:
            st.markdown("## How to query your data\n")
            st.markdown(
                """Enter your question, optionally ask to be alerted.\n"""
            )
            st.markdown("Example: `Are there any planned outages? Alert me of any new planned outages.`")
            st.markdown("## Current Alerts:\n")

        # Streamlit UI elements
        st.title("Trading Alert System Notices")
        prompt = st.text_input("What would you like to query?")

        # Display chat messages from history on app rerun
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # React to user input
        if prompt:

            # Display user message in chat message container
            with st.chat_message("user"):
                st.markdown(prompt)

            st.session_state.messages.append({"role": "user", "content": prompt})

            for message in st.session_state.messages:
                if message["role"] == "user":
                    st.sidebar.text(f"📩 {message['content']}")

            data = {"query": prompt, "user": "user"}

            response = requests.post(self.url, json=data)

            # Add response message to chat history
            if response.status_code == 200:
                response = response.json()
                with st.chat_message("assistant"):
                    st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                st.error(f"Failed to send data. Status code: {response.status_code}")


if __name__ == "__main__":
    UiMgmt().run()
