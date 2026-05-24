import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = "./chroma_db"

RAG_TEMPLATE = """You are a precise document assistant. Answer using ONLY the context below.
Cite the page number(s) when referencing specific information.
If the answer is not in the context, say exactly: "This document doesn't contain information about that."
Never use outside knowledge. Never make up details.

Context:
{context}

Question: {question}

Answer (include page citations like [Page X]):"""

def format_docs(docs):
    formatted = []
    for i, doc in enumerate(docs, 1):
        page = doc.metadata.get("page", "?")
        formatted.append(f"[Chunk {i} | Page {page}]\n{doc.page_content.strip()}")
    return "\n\n---\n\n".join(formatted)

def get_qa_chain(collection_name: str):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )

    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)

    prompt = PromptTemplate(
        template=RAG_TEMPLATE,
        input_variables=["context", "question"],
    )

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain, retriever