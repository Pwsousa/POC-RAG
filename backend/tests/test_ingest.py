import pytest
from backend.ingest.processor import DocumentProcessor
import os

def test_processor_init():
    processor = DocumentProcessor(persist_directory="data/test_chroma", raw_directory="data/test_raw")
    assert processor.persist_directory == "data/test_chroma"
    assert os.path.exists("data/test_raw")

def test_text_splitting():
    processor = DocumentProcessor()
    from langchain_core.documents import Document
    docs = [Document(page_content="Esta é uma frase de teste que deve ser dividida em chunks para o processamento do RAG.")]
    splits = processor.text_splitter.split_documents(docs)
    assert len(splits) >= 1
    assert "teste" in splits[0].page_content
