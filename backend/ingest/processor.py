import os
import requests
import json
from datetime import datetime
from typing import List
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from bs4 import BeautifulSoup
from huggingface_hub import snapshot_download
from urllib.parse import urljoin, urlparse
import os
import time

class DocumentProcessor:
    def __init__(self, persist_directory: str = "data/chroma", raw_directory: str = "data/raw"):
        self.persist_directory = persist_directory
        self.raw_directory = raw_directory
        self.log_path = os.path.join("data", "indexing_log.json")
        os.makedirs(self.raw_directory, exist_ok=True)
        os.makedirs("data", exist_ok=True)
        
        # Explicitly downloading the model to a local path to avoid cache issues
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        local_model_path = os.path.join(os.getcwd(), "data", "models", "all-MiniLM-L6-v2")
        
        if not os.path.exists(local_model_path):
            print(f"Baixando modelo de embeddings para {local_model_path}...")
            snapshot_download(repo_id=model_name, local_dir=local_model_path, local_dir_use_symlinks=False)
            
        self.embeddings = HuggingFaceEmbeddings(
            model_name=local_model_path
        )
        chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
        chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True
        )
        self.vector_store = None

    def _update_log(self, filename: str, source: str):
        log = []
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'r') as f:
                    log = json.load(f)
            except json.JSONDecodeError:
                log = []
        
        log.append({
            "filename": filename,
            "source": source,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        with open(self.log_path, 'w') as f:
            json.dump(log, f, indent=4)

    def download_ipcc_docs(self, urls: List[str]):
        """Download public IPCC AR6 documents."""
        downloaded_paths = []
        retries = int(os.getenv("DOWNLOAD_RETRIES", "3"))
        for url in urls:
            filename = url.split("/")[-1]
            if not filename.endswith(".pdf"):
                filename += ".pdf"
            path = os.path.join(self.raw_directory, filename)
            if os.path.exists(path) and os.path.getsize(path) > 0:
                downloaded_paths.append(path)
                continue
            attempt = 0
            while attempt < retries:
                attempt += 1
                try:
                    print(f"Baixando {url} (tentativa {attempt}/{retries})...")
                    existing_size = os.path.getsize(path) if os.path.exists(path) else 0
                    headers = {}
                    if existing_size > 0:
                        headers["Range"] = f"bytes={existing_size}-"
                    with requests.get(url, stream=True, timeout=(15, 120), headers=headers) as response:
                        if response.status_code not in (200, 206):
                            print(f"Erro ao baixar {url}: HTTP {response.status_code}")
                            time.sleep(2 * attempt)
                            continue
                        mode = "ab" if existing_size > 0 else "wb"
                        with open(path, mode) as f:
                            for chunk in response.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                        if os.path.getsize(path) > 0:
                            downloaded_paths.append(path)
                            self._update_log(filename, url)
                            break
                except Exception as e:
                    print(f"Erro ao baixar {url}: {e}")
                    time.sleep(2 * attempt)
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                print(f"Falhou o download após {retries} tentativas: {url}")
        return downloaded_paths

    def index_documents(self, file_paths: List[str], web_urls: List[str] = []):
        """Index PDFs and web content into ChromaDB."""
        documents = []
        url_map = {}
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r") as f:
                    entries = json.load(f)
                    for e in entries:
                        url_map[e.get("filename")] = e.get("source")
            except Exception:
                url_map = {}
        
        # Load PDFs
        for path in file_paths:
            loader = PyPDFLoader(path)
            loaded = loader.load()
            src_url = url_map.get(os.path.basename(path))
            if src_url:
                for d in loaded:
                    d.metadata["source_url"] = src_url
            documents.extend(loaded)
            
        # Load Web Content
        if web_urls:
            loader = WebBaseLoader(web_urls)
            loaded = loader.load()
            for d in loaded:
                s = d.metadata.get("source")
                if isinstance(s, str) and s.startswith("http"):
                    d.metadata["source_url"] = s
            documents.extend(loaded)
            
        # Split documents
        splits = self.text_splitter.split_documents(documents)
        
        # Create or update vector store
        if self.vector_store is None:
            self.vector_store = Chroma.from_documents(
                documents=splits,
                embedding=self.embeddings,
                persist_directory=self.persist_directory
            )
        else:
            self.vector_store.add_documents(splits)
        
        return len(splits)

    def get_retriever(self):
        if self.vector_store is None:
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
        search_type = os.getenv("CHROMA_SEARCH_TYPE", "mmr")
        k = int(os.getenv("CHROMA_K", "3"))
        fetch_k = int(os.getenv("CHROMA_FETCH_K", "20"))
        if search_type == "mmr":
            return self.vector_store.as_retriever(
                search_type="mmr",
                search_kwargs={"k": k, "fetch_k": fetch_k, "lambda_mult": 0.5}
            )
        return self.vector_store.as_retriever(search_kwargs={"k": k})

    def discover_ipcc_ar6_resources(self, start_urls: List[str], max_pdfs: int = 10, max_pages: int = 10):
        pdfs = []
        pages = []
        seen = set()
        for u in start_urls:
            try:
                r = requests.get(u, timeout=20)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a"):
                    href = a.get("href")
                    if not href:
                        continue
                    full = urljoin(u, href)
                    if full in seen:
                        continue
                    seen.add(full)
                    pr = urlparse(full)
                    if "ipcc.ch" not in pr.netloc:
                        continue
                    if "/report/ar6/" not in pr.path:
                        continue
                    if full.lower().endswith(".pdf"):
                        pdfs.append(full)
                    else:
                        pages.append(full)
                if len(pdfs) >= max_pdfs and len(pages) >= max_pages:
                    break
            except Exception:
                continue
        pdfs = list(dict.fromkeys(pdfs))[:max_pdfs]
        pages = list(dict.fromkeys(pages))[:max_pages]
        return pdfs, pages

    def bootstrap_index_ipcc_ar6(self, max_pdfs: int = 8, max_pages: int = 8):
        seeds = [
            "https://www.ipcc.ch/report/ar6/wg1/",
            "https://www.ipcc.ch/report/ar6/wg2/",
            "https://www.ipcc.ch/report/ar6/wg3/",
        ]
        pdf_urls, page_urls = self.discover_ipcc_ar6_resources(seeds, max_pdfs=max_pdfs, max_pages=max_pages)
        pdf_paths = self.download_ipcc_docs(pdf_urls)
        return self.index_documents(pdf_paths, web_urls=page_urls)

if __name__ == "__main__":
    # Test ingestion
    processor = DocumentProcessor()
    seeds = [
        "https://www.ipcc.ch/report/ar6/wg1/",
        "https://www.ipcc.ch/report/ar6/wg2/downloads/report/IPCC_AR6_WGII_SummaryForPolicymakers.pdf",
        "https://www.ipcc.ch/report/ar6/wg3/downloads/report/IPCC_AR6_WGIII_SPM.pdf"
    ]
    ipcc_urls, _pages = processor.discover_ipcc_ar6_resources(seeds, max_pdfs=60, max_pages=0)
    paths = processor.download_ipcc_docs(ipcc_urls)
    count = processor.index_documents(paths)
    print(f"Indexados {count} trechos de documentos.")
