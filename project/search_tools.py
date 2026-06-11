# Contains our search tool implementation

from typing import List, Any

class SearchTool:
    def __init__(self, index):
        self.index = index

    def search(self, query: str) -> List[Any]:
        """
        Perform a text-based search on the FAQ index.

        args:
            query (str): The search query string.
        
        Returns:
            List[Any]: A list of up to 5 search results returned by the FAQ index.
        """
        return self.index.search(query, num_results=5)

        #I created a class instead of just a function like we had in the Jupyter notebook. Previously, it was a global variable that we referenced from a function. Now the index is encapsulated inside a class with tools, which makes the code more organized.
        