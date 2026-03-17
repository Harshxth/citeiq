from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.rag import ingest_documents, retrieve, get_llm
from langchain_core.messages import HumanMessage
import shutil
import os

app = FastAPI(title="CiteIQ", version="1.0")

# ── Request/Response models ────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    sources: list[str]

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
    # Step 1: retrieve relevant chunks
    chunks = retrieve(request.question)

    if not chunks:
        raise HTTPException(status_code=404, detail="No relevant documents found")

    # Step 2: build context from chunks
    context = "\n\n".join([chunk.page_content for chunk in chunks])
    sources = [chunk.metadata.get("source", "unknown") for chunk in chunks]

    # Step 3: build prompt
    prompt = f"""You are a helpful assistant. Answer the question based ONLY on the context below.
If the answer is not in the context, say "I don't have enough information to answer this."

Context:
{context}

Question: {request.question}

Answer:"""

    # Step 4: call Groq
    llm = get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])

    return QueryResponse(answer=response.content, sources=list(set(sources)))