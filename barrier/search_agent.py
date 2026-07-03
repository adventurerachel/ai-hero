"""
search_agent.py
 
Creates and configures the pydantic-ai Agent for the Barrier AI FAQ
assistant.
 
Defines the system prompt that governs the agent's behaviour (mandatory
search-before-answer, citation requirements) and init_agent(), which
wires a fitted search index up as a callable "search" tool the LLM can
invoke mid-conversation.
"""

import search_tools
from pydantic_ai import Agent, Tool
from minsearch import Index

SYSTEM_PROMPT_TEMPLATE = """
You are a retrieval-grounded assistant for the {repo_name} repository.

RULES:
- You MUST use the search tool before answering any question.
- Never answer from general knowledge alone.
- If search returns no results, say you cannot find relevant documentation.
- Base your answer ONLY on the retrieved search results.

CITATIONS (required for every factual answer):
- After using information from a search result, cite it using its `github_url` field.
- Format each citation as a Markdown link: [path](github_url)
- Use the exact `github_url` value returned by the search tool. Never invent or guess a URL.
- If a result has no `github_url`, state that no source path was available for that result.
- Include at least one citation per factual claim, placed at the end of the relevant sentence or paragraph.


If context is insufficient, say so clearly and provide general guidance.

"""

def init_agent(
    index: Index, 
    repo_owner: str, 
    repo_name: str, 
    branch: str = "master", 
    model: str= "gpt-4o-mini"
) -> Agent:
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(repo_owner=repo_owner, repo_name=repo_name)

    search_tool = search_tools.SearchTool(
        index=index,
        repo_owner=repo_owner,
        repo_name=repo_name,
        branch=branch
        )

    agent = Agent(
        name="barrier_rag_agent",
        system_prompt=system_prompt,
        model=model,

        tools=[
            Tool(
                name="search",
                # This description is part of the prompt: the LLM reads
                # it to decide when the search tool should be called.

                description="Searches the Barrier documentation and returns relevant passages",
                function=search_tool.search
            )
        ],
    )

    return agent

def require_context(search_results):
    if not search_results:
        return "No relevant documentation found for this query."

    return "\n\n".join(
        r.content for r in search_results if r.content
    )

def build_context(results: list[dict]) -> str:
    blocks = []

    for r in results:
        blocks.append(
            f"""
SOURCE:

{r.get("text", "")}

CITATION:
{r.get("citation", "NO_CITATION")}
"""
        )
    
    return "\n\n---\n\n".join(blocks)