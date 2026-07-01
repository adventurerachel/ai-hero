import io
import zipfile
import requests
import frontmatter

from minsearch import Index


def read_repo_data(repo_owner, repo_name):
    resp = None
    for branch in ["master", "main"]:
        url = f"https://github.com/{repo_owner}/{repo_name}/archive/refs/heads/{branch}.zip"
        print(f"[read_repo_data] requesting {url}")
        try:
            resp = requests.get(url, timeout=60)
        except requests.exceptions.RequestException as e:
            print(f"[read_repo_data] request failed for branch '{branch}: {e}")
            continue
        print(f"[read_repo_data] got status {resp.status_code}")
        if resp.status_code == 200 and "zip" in resp.headers.get("Content-Type", ""):
            break
    else:
        raise RuntimeError("Could not download repo ZIP from main or master")

    repository_data = []
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    for file_info in zf.infolist():
        filename = file_info.filename.lower()
        if not (filename.endswith('.md') or filename.endswith('.mdx')):
            continue
        with zf.open(file_info) as f_in:
            content = f_in.read()
            post = frontmatter.loads(content)
            data = post.to_dict()

            _, filename_repo = file_info.filename.split('/', maxsplit=1)
            data['filename'] = filename_repo
            repository_data.append(data)

    zf.close()

    print(f"[read_repo_data] downloaded from branch '{branch}', found {len(repository_data)} markdown documents")
    return repository_data, branch

def sliding_window(seq, size, step):
    if size <= 0 or step <= 0:
        raise ValueError("size and step must be positive")

    n = len(seq)
    result = []
    for i in range(0, n, step):
        batch = seq[i:i+size]
        result.append({'start': i, 'content': batch})
        if i + size > n:
            break

    return result


def chunk_documents(docs, size=2000, step=1000):
    chunks = []

    for doc in docs:
        doc_copy = doc.copy()
        doc_content = doc_copy.pop('content')
        doc_chunks = sliding_window(doc_content, size=size, step=step)
        for chunk in doc_chunks:
            chunk.update(doc_copy)
        chunks.extend(doc_chunks)
    return chunks


def index_data(
        repo_owner,
        repo_name,
        filter_func=None,
        chunk=False,
        chunking_params=None,
    ):
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
