![CI Pipeline](https://github.com/shaneboby2004/pdf-qa-rag/actions/workflows/ci.yml/badge.svg)
# PDF Q&A RAG System

A full-stack AI application that lets you upload any PDF and ask natural language questions about it, with streaming answers and source citations.

## Tech Stack

**Backend:** Python, FastAPI, LangChain, ChromaDB, Google Gemini Embeddings, Groq (Llama 3)  
**Frontend:** Angular, TypeScript

## Features

- Upload any PDF and index it instantly in the background
- Ask natural language questions and get streamed answers token by token
- Source citations with page numbers for every answer
- Duplicate PDF detection — re-uploads return cached results instantly
- Clean two-panel chat UI with typing indicators

## Architecture

PDF Upload → PyMuPDF → Chunking → Gemini Embeddings → ChromaDB
User Query → Embed Query → Similarity Search → Groq LLM → Streamed Response


## Running Locally

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
ng serve
```

Add a `.env` file in `/backend`:

GOOGLE_API_KEY= your_key
GROQ_API_KEY= your_key


Open `http://localhost:4200` to use the app.