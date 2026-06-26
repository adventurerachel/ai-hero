# Handles data loading and indexing from GitHub repositories

import io
import zipfile
import requests
import frontmatter

from minsearch import Index

def read_repo_data(repo_owner: str, repo_name: str) -> list[dict]:
    """
    Downloads a GitHub repository as a zip file and extracts metadata and content 
    from all Markdown (.md) and MDX (.mdx) files.

    Args:
        repo_owner (str): The GitHub username or organization that owns the repository.
        repo_name (str): The name of the repository.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents a document.
                    It contains the parsed frontmatter metadata, the document content 
                    under the 'content' key, and the relative file path under 'filename'.
    """
    url = f'https://codeload.github.com/{repo_owner}/{repo_name}/zip/refs/heads/main'
    resp = requests.get(url)

    # Ensure the request was successful before trying to parse the zip
    resp.raise_for_status()

    repository_data = []

    zf = zipfile.ZipFile(io.BytesIO(resp.content))

    for file_info in zf.infolist():
        # Skip directories to prevent errors when calling zf.open()
        if file_info.is_dir():
            continue

        filename = file_info.filename.lower()

        if not (filename.endswith('.md') or filename.endswith('.mdx')):
            continue

        with zf.open(file_info) as f_in:
            content = f_in.read()
            post = frontmatter.loads(content)

            # to_dict() includes both the frontmatter metadata AND the markdown body
            # under the 'content' key.
            data = post.to_dict()

            _, filename_repo = file_info.filename.split('/', maxsplit=1)
            data['filename'] = filename_repo
            repository_data.append(data)

    zf.close()
    return repository_data

def sliding_window(seq: str, size: int, step: int) -> list[dict]:
    """
    Splits a sequence (like a string) into overlapping chunks using a sliding window approach.

    Args:
        seq (str): The sequence to be chunked.
        size (int): The maximum size of each chunk.
        step (int): The number of elements to step forward for the next chunk.

    Returns:
        list[dict]: A list of dictionaries, each containing the 'start' index 
                    and the 'content' of the chunk.
    """
    if size <= 0 or step <= 0:
        raise ValueError("size and step must be positive")

    n = len(seq)
    result = []
    for i in range(0, n, step):
        batch = seq[i:i+size]
        result.append({'start': i, 'content':batch})

        # If this chunk reached the end of the sequence, stop generating more
        if i + size > n:
            break
    
    return result

def chunk_documents(docs: list[dict], size: int=2000, step: int=1000) -> list[dict]:
    """
    Chunks the 'content' field of a list of documents using a sliding window, 
    while preserving the original document metadata in each chunk.

    Args:
        docs (list[dict]): The list of document dictionaries to chunk.
        size (int, optional): The maximum character size of each chunk. Defaults to 2000.
        step (int, optional): The character step size between chunks. Defaults to 1000.

    Returns:
        list[dict]: A new list of document dictionaries, where each represents a chunk.
    """
    chunks = []

    for doc in docs:
        doc_copy = doc.copy()
        doc_content = doc_copy.pop('content')
        doc_chunks = sliding_window(doc_content, size=size, step=step)
        # Add the original metadata back into each chunk
        for chunk in doc_chunks:
            chunk.update(doc_copy)
        chunks.extend(doc_chunks)
    
    return chunks

def index_data(
        repo_owner: str,
        repo_name: str,
        filter_func=None,
        chunk: bool = False,
        chunking_params: dict =None,
    ) -> Index:
    """
    Orchestrates the data ingestion pipeline: downloads the repo, filters documents, 
    optionally chunks them, and indexes them using minsearch.

    Args:
        repo_owner (str): The GitHub username or organization.
        repo_name (str): The repository name.
        filter_func (callable, optional): A function that takes a document dict and 
                                          returns True to keep it or False to discard it.
                                          Defaults to None (keeps all documents).
        chunk (bool, optional): Whether to chunk the documents before indexing. Defaults to False.
        chunking_params (dict, optional): Parameters for chunking ('size' and 'step'). 
                                          Defaults to {'size': 2000, 'step': 1000}.

    Returns:
        Index: A fitted minsearch Index object ready for querying.
    """
    docs = read_repo_data(repo_owner, repo_name)

    if filter_func is not None:
        docs = [doc for doc in docs if filter_func(doc)]

    if chunk:
        if chunking_params is None:
            chunking_params = {'size':2000, 'step': 1000}
        docs = chunk_documents(docs, **chunking_params)
    
    index = Index(
        text_fields=["content", "filename"],
    )

    index.fit(docs)
    return index