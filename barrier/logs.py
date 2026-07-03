"""
Utilities for logging conversations with PydanticAI agents.

This module converts conversations into JSON and writes them
to disk for later inspection and debugging.

Note: on ephemeral hosting environments (e.g. Streamlit Community
Cloud), the log directory created here is wiped on every app
restart/reboot/redeploy, since these platforms don't provide
persistent local disk storage. This module is best suited for local
development and debugging; long-term log retention on a deployed app
would need external storage (e.g. a database or object store).
"""

import os
import json
import secrets
from pathlib import Path
from datetime import datetime
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessagesTypeAdapter

# Configurable via the LOGS_DIRECTORY environment variable, defaulting
# to a local "logs" folder. Created at import time.
LOG_DIR = Path(os.getenv('LOGS_DIRECTORY', 'logs'))
LOG_DIR.mkdir(exist_ok=True)

def log_entry(agent, messages, source='user'):
    """
    Build a JSON-serialisable dict summarising one agent conversation.
 
    Args:
        agent: The Agent instance that handled the conversation.
        messages: The list of new messages produced during this run
            (as returned by result.new_messages()).
        source: A free-text label for where this interaction came from
            (e.g. "user" for live chat traffic). Useful for filtering
            logs later if multiple sources feed into the same log dir.
 
    Returns:
        A dict containing the agent's configuration (name, system
        prompt, model, available tools) alongside the full serialised
        message history for this interaction.
    """

    # Collect the names of every tool the agent had available during
    # this conversation (e.g. "search"), for later debugging context.
    tools = []
    for ts in agent.toolsets:
        tools.extend(ts.tools.keys())

    # pydantic-ai messages are structured objects, not plain dicts —
    # this converts them into JSON-writable plain Python data.
    dict_messages = ModelMessagesTypeAdapter.dump_python(messages)

    return {
        "agent_name": agent.name,
        # NOTE: agent._instructions is a private/internal attribute of
        # the pydantic-ai Agent class (leading underscore). It works as
        # of pydantic-ai==1.0.9, but isn't part of the public API, so
        # it could change or be removed in a future version upgrade.
        "system_prompt": agent._instructions,
        "provider": agent.model.system,
        "model": agent.model.model_name,
        "tools": tools,
        "messages": dict_messages,
        "source": source
    }

def serializer(obj):
    """
    Fallback JSON serialiser for object types json.dump doesn't handle
    natively — currently just datetime objects, converted to ISO format.
 
    Passed to json.dump via the `default=` argument; called only for
    objects the standard encoder can't handle on its own.
 
    Raises:
        TypeError: for any object type this function doesn't know how
            to serialise, matching json.dump's expected behaviour for
            an unhandled `default` callback.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def log_interaction_to_file(agent, messages, source='user'):
    """
    Write a single conversation to a JSON file on disk.
 
    Args:
        agent: The Agent instance that handled the conversation.
        messages: The list of new messages produced during this run.
        source: A free-text label for where this interaction came from.
 
    Returns:
        The path to the written log file.
 
    Raises:
        ValueError: if `messages` is empty, since there's nothing
            meaningful to log.
    """
    if not messages:
        raise ValueError("Cannot log an empty conversation")

    entry = log_entry(agent, messages, source)

    # Use the timestamp of the most recent message to build the
    # filename, so files sort chronologically.
    ts = entry['messages'][-1]['timestamp']
    ts_str = ts.strftime("%Y%m%d_%H%M%S")

    # Random suffix avoids filename collisions if two interactions
    # happen to log within the same second.
    rand_hex = secrets.token_hex(3)

    safe_name = agent.name.replace(" ", "_")
    filename = f"{safe_name}_{ts_str}_{rand_hex}.json"
    filepath = LOG_DIR / filename

    with filepath.open("w", encoding="utf-8") as f_out:
        json.dump(entry, f_out, indent=2, default=serializer)

    return filepath