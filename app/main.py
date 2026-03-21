from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.agent import run_agent
from app.rag import ingest_documents
import shutil
import os

app = FastAPI(title="CiteIQ", version="1.0")

# ── CORS ───────────────────────────────────────────────────────────
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

# ── Health check ───────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "CiteIQ is running"}

# ── Upload + ingest documents ──────────────────────────────────────
@app.post("/ingest")
async def ingest(files: list[UploadFile] = File(...)):
    saved_paths = []

    os.makedirs("data", exist_ok=True)

    for file in files:
        path = f"data/{file.filename}"
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        saved_paths.append(path)

    ingest_documents(saved_paths)
    return {"message": f"Ingested {len(saved_paths)} file(s) successfully"}

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