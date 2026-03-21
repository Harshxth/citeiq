from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from app.agent import run_agent
from app.rag import ingest_documents
from app.ingest_on_startup import startup_ingest
import shutil
import os
import base64

@asynccontextmanager
async def lifespan(app):
    startup_ingest()
    yield

app = FastAPI(title="CiteIQ", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request/Response models ────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    eval_scores: dict = {}
    retry_count: int = 0
    route: str = ""

class IngestRequest(BaseModel):
    filename: str
    content_b64: str

# ── Health check ───────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "CiteIQ is running"}

# ── Upload + ingest documents ──────────────────────────────────────
@app.post("/ingest")
async def ingest(request: IngestRequest):
    os.makedirs("data", exist_ok=True)

    file_bytes = base64.b64decode(request.content_b64)
    path = f"data/{request.filename}"

    with open(path, "wb") as f:
        f.write(file_bytes)

    ingest_documents([path])
    return {"message": f"Ingested {request.filename} successfully"}

# ── Query endpoint ─────────────────────────────────────────────────
@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    result = run_agent(request.question)

    if not result["answer"]:
        raise HTTPException(status_code=404, detail="No answer generated")

    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        eval_scores=result.get("eval_scores", {}),
        retry_count=result.get("retry_count", 0),
        route=result.get("route", "")
    )