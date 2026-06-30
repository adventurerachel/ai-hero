# --- 1. LOAD ENVIRONMENT VARIABLES FIRST ---
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve()

for parent in env_path.parents:
    candidate = parent / ".env"
    if candidate.exists():
        load_dotenv(candidate)
        break
# -------------------------------------------

import asyncio
import streamlit as st
from dataclasses import dataclass
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

import ingest
import search_agent
import logs

REPO_OWNER = "debauchee"
REPO_NAME = "barrier"

# --- HELPER FUNCTIONS FOR ASYNC STREAMING ---

@dataclass
class StreamHolder:
    """A simple container to capture the new messages after the async stream finishes."""
    new_messages: list = None

def stream_async(async_gen):
    """
    Helper function to consume an async generator synchronously.
    This allows us to stream async responses from pydantic-ai in Streamlit.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        while True:
            try:
                yield loop.run_until_complete(async_gen.__anext__())
            except StopAsyncIteration:
                break
    finally:
        loop.close()

# FIXED: Added 'agent' as an argument so the function has access to it
async def get_agent_stream(agent, prompt, history, holder):
    """
    Async generator that yields text chunks from the pydantic-ai agent.
    """
    async with agent.run_stream(prompt, message_history=history) as result:
        # Stream the text output token by token
        # (Note: depending on your exact pydantic-ai version, this might be stream_text() instead of stream_output())
        async for text in result.stream_text(debounce_by=0.01): 
            yield text
            
        # Once the stream is complete, capture the new messages for logging
        holder.new_messages = result.new_messages()

# --- STREAMLIT APP LOGIC ---

@st.cache_resource
def initialize_resources():
    st.write("Starting ingestion...")
    
    def doc_filter(doc: dict) -> bool:
    #    return 'barrier' in doc['filename']
        False

    print("[initialize_resources] calling index_data...")        
    index = ingest.index_data(REPO_OWNER, REPO_NAME)  #filter_func=doc_filter)
    print("[initialize_resources] index_data returned")
    st.write("Index created")

    print("[initialize_resources] calling init_agent...")
    agent = search_agent.init_agent(index, REPO_OWNER, REPO_NAME)
    print("[initialize_resources] init_agent returned")
    st.write("Agent created")
        
    return agent

def build_message_history():
    """Converts Streamlit session state messages into Pydantic AI message history format."""
    history = []
    for msg in st.session_state.messages[:-1]:
        if msg["role"] == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=msg["content"])]))
        elif msg["role"] == "assistant":
            history.append(ModelResponse(parts=[TextPart(content=msg["content"])]))
    return history

def main():
    st.set_page_config(page_title="AI FAQ Assistant", page_icon="🤖")
    st.title("AI FAQ Assistant: Barrier")
    st.caption(f"Repository: {REPO_OWNER}/{REPO_NAME}")

    # 1. Initialize Agent
    agent = initialize_resources()

    # 2. Initialize Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 3. Display Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 4. Handle User Input
    if prompt := st.chat_input("Ask a question about Barrier"):
        # Add and display user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate and stream assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            history = build_message_history()
            holder = StreamHolder()
            
            # FIXED: Passed the 'agent' object into the function here
            for text in stream_async(get_agent_stream(agent, prompt, history, holder)):
                full_response = text
                message_placeholder.markdown(full_response + "▌")
                
            # Finalize the display (remove the blinking cursor)
            message_placeholder.markdown(full_response)

        # Add assistant response to session state
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        
        # Log the interaction using the captured messages
        if holder.new_messages:
            try:
                logs.log_interaction_to_file(agent, holder.new_messages)
            except Exception as e:
                st.warning(f"Could not log interaction: {e}")

if __name__ == "__main__":
    main()