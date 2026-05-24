import os
import shutil
import uuid
import hashlib
import traceback
import json
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from ingest import ingest_pdf
from chain import get_qa_chain

load_dotenv()

app = FastAPI(title="PDF Q&A API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory state
processing_status = {}
hash_to_collection = {}

class QueryRequest(BaseModel):
    question: str
    collection_name: str

# --- Helpers ---

def get_file_hash(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def ingest_with_status(file_path: str, collection_name: str):
    processing_status[collection_name] = "processing"
    try:
        ingest_pdf(file_path, collection_name)
        processing_status[collection_name] = "ready"
    except Exception as e:
        processing_status[collection_name] = f"error: {str(e)}"

# --- Endpoints ---

@app.get("/")
def root():
    return {"status": "running"}

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    collection_name = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{collection_name}.pdf")

    try:
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        file_hash = get_file_hash(save_path)
        if file_hash in hash_to_collection:
            existing = hash_to_collection[file_hash]
            os.remove(save_path)
            return {
                "collection_name": existing,
                "filename": file.filename,
                "status": "ready",
                "cached": True,
            }

        hash_to_collection[file_hash] = collection_name
        processing_status[collection_name] = "processing"
        background_tasks.add_task(ingest_with_status, save_path, collection_name)

        return {
            "collection_name": collection_name,
            "filename": file.filename,
            "status": "processing",
            "cached": False,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{str(e)}\n{traceback.format_exc()}"
        )

@app.get("/status/{collection_name}")
def get_status(collection_name: str):
    status = processing_status.get(collection_name, "unknown")
    return {"collection_name": collection_name, "status": status}

@app.post("/query")
async def query(req: QueryRequest):
    status = processing_status.get(req.collection_name, "unknown")
    if status == "processing":
        raise HTTPException(status_code=409, detail="Document is still being processed. Please wait.")
    if status == "unknown":
        raise HTTPException(status_code=404, detail="Collection not found. Please upload the PDF first.")
    if status.startswith("error"):
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {status}")

    try:
        chain, retriever = get_qa_chain(req.collection_name)
        docs = retriever.invoke(req.question)
        sources = [
            {
                "page": doc.metadata.get("page", "?"),
                "preview": doc.page_content[:200],
            }
            for doc in docs
        ]

        def generate():
            yield f"SOURCES:{json.dumps(sources)}\n"
            for chunk in chain.stream(req.question):
                yield chunk

        return StreamingResponse(generate(), media_type="text/plain")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{str(e)}\n{traceback.format_exc()}"
        )