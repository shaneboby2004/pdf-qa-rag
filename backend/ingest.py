import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = "./chroma_db"

def ingest_pdf(file_path: str, collection_name: str) -> int:
    loader = PyMuPDFLoader(file_path)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = splitter.split_documents(docs)

    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=CHROMA_DIR,
    )

    return len(chunks)