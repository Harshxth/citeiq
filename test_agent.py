from app.agent import run_agent

# Test 1: should trigger retrieval
print("=== Test 1: Medical question ===")
result = run_agent("what are the symptoms of sepsis?")
print(f"Route: {result['route']}")
print(f"Answer: {result['answer']}")
print(f"Sources: {result['sources']}")

# Test 2: should answer directly
print("\n=== Test 2: General question ===")
result = run_agent("what is 2 + 2?")
print(f"Route: {result['route']}")
print(f"Answer: {result['answer']}")
print(f"Sources: {result['sources']}")