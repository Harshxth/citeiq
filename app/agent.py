import os
from typing import TypedDict, Literal
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from app.rag import retrieve, get_llm

load_dotenv()

# ── State ──────────────────────────────────────────────────────────
# This is the object that gets passed between every node
# Each node can read from it and write to it
class AgentState(TypedDict):
    question: str
    context: list
    answer: str
    sources: list[str]
    route: str
    retry_count: int

# ── Node 1: Router ─────────────────────────────────────────────────
# Decides: does this question need retrieval or can we answer directly?
def router_node(state: AgentState) -> AgentState:
    llm = get_llm()
    prompt = f"""You are a routing assistant for a medical document search system.

Your job is to decide if a question should search the document database.

Rules:
- ANY medical, clinical, scientific, or health-related question → "retrieve"
- ANY question about a specific condition, drug, symptom, treatment → "retrieve"  
- ONLY simple math, greetings, or basic general knowledge → "direct"

Question: {state['question']}

Reply with ONLY one word, "retrieve" or "direct":"""

    response = llm.invoke([HumanMessage(content=prompt)])
    route = response.content.strip().lower()

    if route not in ["retrieve", "direct"]:
        route = "retrieve"

    print(f"Router decision: {route}")
    return {**state, "route": route}

# ── Node 2: Retrieve ───────────────────────────────────────────────
def retrieve_node(state: AgentState) -> AgentState:
    chunks = retrieve(state["question"])
    context = [chunk.page_content for chunk in chunks]
    sources = [chunk.metadata.get("source", "unknown") for chunk in chunks]
    print(f"Retrieved {len(chunks)} chunks")
    return {**state, "context": context, "sources": sources}

# ── Node 3: Generate ───────────────────────────────────────────────
def generate_node(state: AgentState) -> AgentState:
    llm = get_llm()

    if state.get("context"):
        context_text = "\n\n".join(state["context"])
        prompt = f"""Answer the question based ONLY on the context below.
If the answer is not in the context, say "I don't have enough information."

Context:
{context_text}

Question: {state['question']}

Answer:"""
    else:
        # Direct answer — no retrieval
        prompt = state["question"]

    response = llm.invoke([HumanMessage(content=prompt)])
    return {**state, "answer": response.content}

# ── Conditional edge: where to go after router ─────────────────────
def route_decision(state: AgentState) -> Literal["retrieve", "generate"]:
    if state["route"] == "retrieve":
        return "retrieve"
    return "generate"

# ── Build the graph ────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", router_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)

    # Entry point
    graph.set_entry_point("router")

    # Conditional edge after router
    graph.add_conditional_edges(
        "router",
        route_decision,
        {
            "retrieve": "retrieve",
            "generate": "generate"
        }
    )

    # After retrieve → always generate
    graph.add_edge("retrieve", "generate")

    # After generate → done
    graph.add_edge("generate", END)

    return graph.compile()

# ── Run the agent ──────────────────────────────────────────────────
def run_agent(question: str) -> dict:
    graph = build_graph()

    initial_state = AgentState(
        question=question,
        context=[],
        answer="",
        sources=[],
        route="",
        retry_count=0
    )

    result = graph.invoke(initial_state)

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "route": result["route"]
    }