from app.rag import ingest_documents
import os

def startup_ingest():
    data_dir = "data"
    if not os.path.exists(data_dir):
        print("No data/ directory found")
        return
    
    files = [
        os.path.join(data_dir, f)
        for f in os.listdir(data_dir)
        if f.endswith((".pdf", ".txt"))
    ]
    
    if files:
        print(f"Auto-ingesting {len(files)} files: {[os.path.basename(f) for f in files]}")
        ingest_documents(files)
    else:
        print("No documents found in data/ directory")