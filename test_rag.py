from app.rag import ingest_documents, retrieve, get_llm
from langchain_core.messages import HumanMessage

# Test 1: ingest
print("--- Ingesting document ---")
ingest_documents(["data/test.txt"])

# Test 2: retrieve
print("\n--- Retrieving chunks ---")
chunks = retrieve("what are the symptoms of sepsis?")
for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}: {chunk.page_content[:100]}...")

# Test 3: LLM
print("\n--- Testing Groq connection ---")
llm = get_llm()
response = llm.invoke([HumanMessage(content="What is sepsis in one sentence?")])
print(f"Groq response: {response.content}")