import os
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_groq import ChatGroq
from langchain.schema import Document

load_dotenv()

# ── Embedding model ────────────────────────────────────────────────
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHROMA_PATH = "chroma_db"

def get_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

# ── Vector store ───────────────────────────────────────────────────
def get_vectorstore():
    return Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=get_embeddings()
    )

# ── Document ingestion ─────────────────────────────────────────────
def ingest_documents(file_paths: list[str]):
    docs = []

    for path in file_paths:
        if path.endswith(".pdf"):
            loader = PyPDFLoader(path)
        else:
            loader = TextLoader(path)
        docs.extend(loader.load())

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(docs)

    # Store in ChromaDB
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=CHROMA_PATH
    )
    print(f"Ingested {len(chunks)} chunks into ChromaDB")
    return vectorstore

# ── Retrieval ──────────────────────────────────────────────────────
def retrieve(query: str, k: int = 4) -> list[Document]:
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    return retriever.invoke(query)

# ── LLM ───────────────────────────────────────────────────────────
def get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        api_key=os.getenv("GROQ_API_KEY")
    )