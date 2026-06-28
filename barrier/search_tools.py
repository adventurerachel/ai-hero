# Search tool implementation

from typing import Any
from minsearch import Index

class SearchTool:
    """
    Wraps a MinSearch index so it can be used as a tool by a
    Pydantic AI agent.

    The agent only needs to know how to perform searches.
    This class hides the implementation details of the underlying
    search index.
    """

    def __init__(self, index: Index, num_results: int = 5):
        """
        Initialise the search tool.

        Args:
            index: A fitted MinSearch index.
            num_results: Maximum number of search results to return.
        """

    def search(self, query: str) -> list[Any]:
        """
        Search the indexed documents.

        Args:
            query: Natural language search query.

        Returns:
            A list of matching documents ranked by relevance.
        """
        if not query.strip():
            return []
        
        return self.index.search(
            query,
            num_results=self.num_results,
        )