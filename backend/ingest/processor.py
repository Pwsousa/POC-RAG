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
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
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
        for url in urls:
            filename = url.split("/")[-1]
            if not filename.endswith(".pdf"):
                filename += ".pdf"
            path = os.path.join(self.raw_directory, filename)
            
            if not os.path.exists(path):
                print(f"Baixando {url}...")
                response = requests.get(url, stream=True, timeout=60)
                if response.status_code == 200:
                    with open(path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    downloaded_paths.append(path)
                    self._update_log(filename, url)
                else:
                    print(f"Erro ao baixar {url}: {response.status_code}")
            else:
                downloaded_paths.append(path)
        return downloaded_paths

    def index_documents(self, file_paths: List[str], web_urls: List[str] = []):
        """Index PDFs and web content into ChromaDB."""
        documents = []
        
        # Load PDFs
        for path in file_paths:
            loader = PyPDFLoader(path)
            documents.extend(loader.load())
            
        # Load Web Content
        if web_urls:
            loader = WebBaseLoader(web_urls)
            documents.extend(loader.load())
            
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
        return self.vector_store.as_retriever(search_kwargs={"k": 3})

if __name__ == "__main__":
    # Test ingestion
    processor = DocumentProcessor()
    ipcc_urls = [
        "https://www.ipcc.ch/report/ar6/wg1/downloads/report/IPCC_AR6_WGI_SPM.pdf",
        "https://www.ipcc.ch/report/ar6/wg2/downloads/report/IPCC_AR6_WGII_SummaryForPolicymakers.pdf",
        "https://www.ipcc.ch/report/ar6/wg3/downloads/report/IPCC_AR6_WGIII_SPM.pdf"
    ]
    paths = processor.download_ipcc_docs(ipcc_urls)
    count = processor.index_documents(paths)
    print(f"Indexados {count} trechos de documentos.")
