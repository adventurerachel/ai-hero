"""
ingest.py
 
Data pipeline for the Barrier AI FAQ assistant.
 
Responsible for:
1. Fetching: downloading a GitHub repository as a zip archive.
2. Transforming: extracting Markdown documents and (optionally) splitting
   long documents into smaller, overlapping chunks.
3. Indexing: building a searchable minsearch.Index over the resulting
   documents, ready for retrieval by the search agent.
"""


import io
import zipfile
import requests
import frontmatter

from minsearch import Index

from typing import Any, Callable, Optional

def read_repo_data(repo_owner: str, repo_name: str) -> tuple[list[dict[str, Any]], str]:
    """
    Download a GitHub repository's Markdown documentation.
 
    Tries the "master" branch first, then falls back to "main", since
    repositories may use either as their default branch. Network failures
    on one branch (timeouts, connection errors) don't stop the function —
    it simply moves on to try the next branch.
 
    Args:
        repo_owner: GitHub username or organisation that owns the repo.
        repo_name: Name of the repository.
 
    Returns:
        A tuple of:
        - repository_data: list of dicts, one per Markdown file, each
          containing at least 'content' (the document body) and
          'filename' (path relative to the repo root).
        - branch: the branch name ("master" or "main") the data was
          successfully downloaded from.
 
    Raises:
        RuntimeError: if neither "master" nor "main" could be downloaded
            (e.g. wrong repo name, both requests failed/timed out).
    """

    resp = None
    for branch in ["master", "main"]:
        url = f"https://github.com/{repo_owner}/{repo_name}/archive/refs/heads/{branch}.zip"
        print(f"[read_repo_data] requesting {url}")
        try:
            # timeout=60 prevents a slow/unresponsive connection from
            # hanging the whole app indefinitely.
            resp = requests.get(url, timeout=60)
        except requests.exceptions.RequestException as e:
            # Catches timeouts, DNS failures, connection resets, etc.
            # Log and try the next branch rather than crashing.
            print(f"[read_repo_data] request failed for branch '{branch}: {e}")
            continue
        print(f"[read_repo_data] got status {resp.status_code}")
        # A 200 status alone isn't proof of a valid zip — also check
        # the Content-Type header to guard against unexpected HTML
        # error pages being returned with a 200.
        if resp.status_code == 200 and "zip" in resp.headers.get("Content-Type", ""):
            break
    else:
        # This 'else' belongs to the 'for' loop (not an if/else): it
        # only runs if the loop finished WITHOUT hitting 'break',
        # i.e. neither branch produced a valid zip.
        raise RuntimeError("Could not download repo ZIP from main or master")

    repository_data = []
    # Wrap the raw response bytes in a file-like object so zipfile can
    # read it directly from memory, without saving to disk first.
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    for file_info in zf.infolist():
        filename = file_info.filename.lower()
        # Only interested in Markdown documentation, skip everything else
        # (source code, images, config files, etc.)
        if not (filename.endswith('.md') or filename.endswith('.mdx')):
            continue
        with zf.open(file_info) as f_in:
            content = f_in.read()
            # Many Markdown files begin with a YAML "frontmatter" block
            # (e.g. title, date) before the actual content. This splits
            # metadata from body text.
            post = frontmatter.loads(content)
            data = post.to_dict() # body text lands under data['content']

            # GitHub's zip wraps everything in a top-level folder, e.g.
            # "barrier-master/README.md". Strip that off so we're left
            # with a clean path relative to the repo root: "README.md".
            _, filename_repo = file_info.filename.split('/', maxsplit=1)
            data['filename'] = filename_repo
            repository_data.append(data)

    zf.close()

    print(f"[read_repo_data] downloaded from branch '{branch}', found {len(repository_data)} markdown documents")
    return repository_data, branch

def sliding_window(seq: str, size: int, step: int) -> list[dict[str, Any]]:
    """
    Split a sequence (typically a string) into overlapping windows.
 
    Args:
        seq: The sequence to split (e.g. document text).
        size: Length of each window.
        step: How far to advance between windows. If step < size,
            consecutive windows overlap — useful so information near a
            chunk boundary isn't lost entirely to one side.
 
    Returns:
        A list of dicts, each with:
        - 'start': the index in `seq` where this window begins.
        - 'content': the windowed slice of `seq`.
 
    Raises:
        ValueError: if size or step is not positive.
    """
    if size <= 0 or step <= 0:
        raise ValueError("size and step must be positive")

    n = len(seq)
    result = []
    for i in range(0, n, step):
        batch = seq[i:i+size]
        result.append({'start': i, 'content': batch})
        # Stop once a window reaches the end of the sequence, to avoid
        # generating a trailing near-empty window past the content.
        if i + size > n:
            break

    return result


def chunk_documents(docs: list[dict[str, Any]], size: int = 2000, step: int=1000) -> list[dict[str, Any]]:
    """
    Split each document's content into smaller overlapping chunks,
    while preserving the document's other metadata (e.g. filename) on
    every resulting chunk.
 
    Args:
        docs: List of document dicts, each containing a 'content' field.
        size: Chunk length, in characters, passed to sliding_window.
        step: Step size, in characters, passed to sliding_window.
 
    Returns:
        A flat list of chunk dicts. Each chunk has 'start', 'content',
        plus all of the original document's non-content fields (e.g.
        'filename').
    """
    chunks = []

    for doc in docs:
        # Copy to avoid mutating the original document dict.
        doc_copy = doc.copy()
        doc_content = doc_copy.pop('content')
        doc_chunks = sliding_window(doc_content, size=size, step=step)
        # Re-attach the document's other fields (filename, etc.) onto
        # every chunk so each chunk still knows which file it came from.
        for chunk in doc_chunks:
            chunk.update(doc_copy)
        chunks.extend(doc_chunks)
    return chunks

def index_data(
        repo_owner: str,
        repo_name: str,
        filter_func: Optional[Callable[[dict[str, Any]], bool]]=None,
        chunk: bool = False,
        chunking_params: Optional[dict[str, int]]=None,
    ) -> tuple[Index, str]:
    """
    Build a searchable index of a GitHub repository's Markdown documentation.
 
    This is the main entry point for the ingestion pipeline: it fetches,
    optionally filters and chunks, then indexes the documents.
 
    Args:
        repo_owner: GitHub username or organisation that owns the repo.
        repo_name: Name of the repository.
        filter_func: Optional callable taking a document dict and
            returning True/False, to include only documents matching
            some condition (e.g. a specific folder).
        chunk: If True, split long documents into smaller overlapping
            chunks via chunk_documents before indexing.
        chunking_params: Optional dict with 'size' and 'step' keys to
            control chunking behaviour. Defaults to
            {'size': 2000, 'step': 1000} if chunk=True and this is None.
 
    Returns:
        A tuple of:
        - index: a fitted minsearch.Index over the 'content' and
          'filename' fields, ready to be searched.
        - branch: the branch name the source data was downloaded from
          (needed downstream to build correct citation URLs).
    """

    docs, branch = read_repo_data(repo_owner, repo_name)
    print(f"[index_data] total documents read: {len(docs)}")
    print(docs[0])

    if filter_func is not None:
        docs = [doc for doc in docs if filter_func(doc)]
        print(f"[index_data] documents remaining after filter: {len(docs)}")

    if chunk:
        if chunking_params is None:
            chunking_params = {'size': 2000, 'step': 1000}
        docs = chunk_documents(docs, **chunking_params)
        print(f"[index_data] chunking enabled (size={chunking_params['size']}, step={chunking_params['step']}) -> {len(docs)} chunks")

    index = Index(
        text_fields=["content", "filename"],
    )
    print(f"[index_data] about to index {len(docs)} docs")
    if docs:
        print(f"[index_data] sample doc keys: {list(docs[0].keys())}")
        print(f"[index_data] sample content length: {len(docs[0].get('content', ''))}")
    index.fit(docs)

    print(f"[index_data] indexed {len(docs)} items into the search index")
    return index, branch
