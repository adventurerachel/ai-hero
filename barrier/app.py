"""
app.py
 
Streamlit UI for the Barrier AI FAQ assistant.
 
Responsible for:
1. Loading environment variables (e.g. API keys) from a .env file.
2. Initialising the search index and LLM agent once per app process
   (cached via st.cache_resource).
3. Rendering the chat interface and streaming the agent's responses
   token-by-token as they're generated.
4. Logging each interaction for later review.
"""

# --- 1. LOAD ENVIRONMENT VARIABLES FIRST ---
# Must happen before any modules that read env vars at import time
# (e.g. API client libraries) are imported below.
from pathlib import Path
from typing import AsyncGenerator
from dotenv import load_dotenv

# Walk up from this script's own location through every parent folder
# until a .env file is found, rather than assuming one sits in the
# current working directory (which varies depending on how the app
# is launched).
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
    """
    Mutable side-channel for retrieving data from an async generator
    after it finishes streaming.
 
    get_agent_stream() only yields text chunks via `yield`, so this
    object is used to smuggle out result.new_messages() (needed for
    logging) once streaming completes, without changing the generator's
    yield type.
    """
    new_messages: list = None

def stream_async(async_gen: AsyncGenerator[str, None]) -> Iterator[str]:
    """
    Consume an async generator synchronously, yielding each item as
    it arrives.
 
    Streamlit's main script execution is synchronous, but pydantic-ai's
    streaming API is async. This bridges the two by manually driving
    the async generator one step at a time on a dedicated event loop.
 
    Args:
        async_gen: An async generator yielding text chunks.
 
    Yields:
        Each text chunk, synchronously, in the order produced.
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
async def get_agent_stream(
        agent: Agent, 
        prompt: str, 
        history: list[ModelMessage], 
        holder: StreamHolder
    ) -> AsyncGenerator[str, None]:
    """
    Async generator that yields the agent's response text as it streams in.
 
    Args:
        agent: The configured pydantic-ai Agent to run.
        prompt: The user's current question.
        history: Prior conversation turns, for context.
        holder: A StreamHolder to populate with the run's new messages
            once streaming completes, for later logging.
 
    Yields:
        The cumulative response text so far, each time more text
        arrives (not just the newly added delta).
    """
    async with agent.run_stream(prompt, message_history=history) as result:
        # Stream the text output token by token
        # debounce_by batches rapid token updates (every 10ms) rather
        # than yielding on every single token, reducing UI re-render
        # overhead.
        # (Note: depending on your exact pydantic-ai version, this might be stream_text() instead of stream_output())
        async for text in result.stream_text(debounce_by=0.01): 
            yield text
            
        # Once the stream is complete, capture the new messages for logging
        # Only available once the stream has fully completed.
        holder.new_messages = result.new_messages()

# --- STREAMLIT APP LOGIC ---

@st.cache_resource
def initialize_resources() -> Agent:
    """
    Download the repository, build the search index, and construct the
    LLM agent.
 
    Wrapped in @st.cache_resource so this expensive setup (network
    download, index build, agent construction) runs exactly once per
    app process, rather than on every Streamlit script rerun (which
    happens on essentially every user interaction).
 
    Returns:
        A configured Agent, ready to answer questions about the
        repository's documentation.
    """
    st.write("Starting ingestion...")
    
    print("[initialize_resources] calling index_data...")        
    index, branch = ingest.index_data(REPO_OWNER, REPO_NAME)  #filter_func=doc_filter)
    print("[initialize_resources] index_data returned")
    st.write("Index created")

    print("[initialize_resources] calling init_agent...")
    # branch is passed through so citation URLs point to the branch the
    # documents were actually downloaded from, rather than assuming
    # "master".  
    agent = search_agent.init_agent(index, REPO_OWNER, REPO_NAME, branch=branch)
    print("[initialize_resources] init_agent returned")
    st.write("Agent created")
        
    return agent

def build_message_history():
    """
    Converts Streamlit session state messages into Pydantic AI message history format.

    Excludes the most recent message, since that's the current user
    prompt — it's passed separately as the primary `prompt` argument to
    agent.run_stream(), not included in the history.
 
    Returns:
        A list of ModelRequest/ModelResponse objects representing the
        prior conversation turns.
"""
    history = []
    for msg in st.session_state.messages[:-1]:
        if msg["role"] == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=msg["content"])]))
        elif msg["role"] == "assistant":
            history.append(ModelResponse(parts=[TextPart(content=msg["content"])]))
    return history

def main():
    """
    Render the Streamlit chat interface and handle the request/response
    cycle for each user question.
    """
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