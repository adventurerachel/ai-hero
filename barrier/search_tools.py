# Search tool implementation

from typing import Any, List, Dict
import logging
from pydantic import BaseModel, Field
from minsearch import Index
from pprint import pprint

logger = logging.getLogger(__name__)

class SearchResult(BaseModel):
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SearchTool:
    """
    RAG search wrapper around a MinSearch index.

    Responsibilities:
    - Query the index
    - Enrich results with citation-ready metadata
    - Return stable dict structures for the LLM
    """

    def __init__(self, index: Index, repo_owner: str, repo_name: str, branch: str="master",num_results: int = 5):
        """
        Initialise the search tool.

        Args:
            index: A fitted MinSearch index.
            num_results: Maximum number of search results to return.
        """
        self.index = index
        self.repo_owner=repo_owner
        self.repo_name=repo_name
        self.branch=branch
        self.num_results = num_results
        self.logger = logging.getLogger(self.__class__.__name__)

    def search(self, query: str) -> list[Dict[str, Any]]:
        """
        Search the indexed documents and return citation-ready results.

        Args:
            query: Natural language search query.

        Returns:
            A list of matching documents ranked by relevance.
        """
        print("DEBUG QUERY TYPE:", type(query), query)
        query = str(query or "").strip()
        if not query:
            self.logger.warning("Empty query received")
            return []

        self.logger.info(f"SEARCH QUERY: {query}")

        try:
            results = self.index.search(query, num_results=self.num_results)
        except Exception:
            self.logger.exception("Index search failed")
            return []
        
        enriched_results = []

        for r in results or []:
            # Normalise expected fields
            text = r.get("text") or r.get("content") or ""
            path = r.get("path") or r.get("file") or r.get("filename") or None

            github_url = None
            if path:
                github_url = (
                    f"https://github.com/{self.repo_owner}/{self.repo_name}"
                    f"/blob/{self.branch}/{path}"
                )

            enriched_results.append({
                "text": text,
                "path": path,
                "score": r.get("score"),
                "github_url": github_url,
                "raw": r # full original record for debugging
            })
        
       

        #     structured.append(
        #         SearchResult(
        #             content=r.get("content") or r.get("text") or "",
        #             metadata=r
        #         )
        #     )
        
        # print("TOOL CALLED ✔️:", query)
        
        self.logger.info(f"SEARCH RESULTS: {len(enriched_results)}")

        # DEBUG (optional, remove later)
        for r in enriched_results:
            print("\n🔎 RESULT:")
            print("PATH:", r["path"])
            print("URL:", r["github_url"])
        
        return enriched_results
        # return structured