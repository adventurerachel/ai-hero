import streamlit as st
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

import ingest
import search_agent
import logs

REPO_OWNER = "DataTalksClub"
REPO_NAME = "faq"

@st.cache_resource
def initialize_resources():
    """
    Initialize the index and agent. 
    Cached so it only runs once per session, preventing slow reloads.
    """
    with st.spinner("Initializing data ingestion..."):
        def filter(doc):
            return 'data-engineering' in doc['filename']
        
        index = ingest.index_data(REPO_OWNER, REPO_NAME, filter=filter)
    
    with st.spinner("Initializing search agent..."):
        agent = search_agent.init_agent(index, REPO_OWNER, REPO_NAME)
        
    return agent

def build_message_history():
    """
    Converts Streamlit session state messages into Pydantic AI message history format.
    """
    history = []
    # Exclude the last message (the current user prompt) as it's passed directly to the agent
    for msg in st.session_state.messages[:-1]:
        if msg["role"] == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=msg["content"])]))
        elif msg["role"] == "assistant":
            history.append(ModelResponse(parts=[TextPart(content=msg["content"])]))
    return history

def main():
    st.set_page_config(page_title="AI FAQ Assistant", page_icon="🤖")
    st.title("AI FAQ Assistant")
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
    if prompt := st.chat_input("Ask a question about data engineering..."):
        # Add and display user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate and stream assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # Build the context history for the agent
            history = build_message_history()
            
            # Use the synchronous streaming method to avoid asyncio event loop conflicts in Streamlit
            with agent.run_stream_sync(prompt, message_history=history) as result:
                # Stream the text output token by token
                for text in result.stream_text_sync(debounce_by=0.01):
                    full_response += text
                    message_placeholder.markdown(full_response + "▌")
                
                # Finalize the display (remove the blinking cursor)
                message_placeholder.markdown(full_response)
                
                # Capture the new messages for logging
                new_messages = result.new_messages()

        # Add assistant response to session state
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        
        # Log the interaction (adapted from your CLI code)
        try:
            logs.log_interaction_to_file(agent, new_messages)
        except Exception as e:
            st.warning(f"Could not log interaction: {e}")

if __name__ == "__main__":
    main()