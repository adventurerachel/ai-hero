# Creates and configures the Pydantic AI agent

import search_tools
from pydantic_ai import Agent, Tool

SYSTEM_PROMPT_TEMPLATE = """
You are a retrieval-grounded assistant for the {repo_name} repository.

RULES:
- You MUST use the search tool before answering any question about Barrier.
- Never answer from general knowledge alone.
- If search returns no results, say you cannot find relevant documentation.
- Always base answers ONLY on retrieved context.

When answering:
1. First use search tool
2. Then synthesize only from results
3. Cite retrieved content implicitly by grounding in it

For every factual answer:

1. Include one or more references.
2. Each reference must be the original source document returned by the search tool.
3. If the search results contain a file path, produce a Markdown link in the form:

[relative/path/to/file.md](https://github.com/{repo_owner}/{repo_name}/blob/master/relative/path/to/file.md)
Always use the `github_url` field from search results when citing sources. Never invent URLs.
If no file path is available in the search results, say that no source path was available.

If context is insufficient, say so clearly and provide general guidance.

"""

def init_agent(index, repo_owner: str, repo_name: str, model: str= "gpt-4o-mini") -> Agent:
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(repo_owner=repo_owner, repo_name=repo_name)

    search_tool = search_tools.SearchTool(
        index=index,
        repo_owner=repo_owner,
        repo_name=repo_name
        )

    agent = Agent(
        name="barrier_rag_agent",
        system_prompt=system_prompt,
        model=model,

        tools=[
            Tool(
                name="search",
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