import os
from typing import TypedDict, Literal
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from app.rag import retrieve, get_llm
from app.eval import evaluate_answer

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
    eval_scores: dict 

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
    retry_count = state.get("retry_count", 0)

    if state.get("context"):
        context_text = "\n\n".join(state["context"])
        # On retry, add explicit instruction to be more precise
        retry_note = "\nBe very precise and only state what is explicitly in the context." if retry_count > 0 else ""
        prompt = f"""Answer the question based ONLY on the context below.
If the answer is not in the context, say "I don't have enough information."{retry_note}

Context:
{context_text}

Question: {state['question']}

Answer:"""
    else:
        prompt = state["question"]

    response = llm.invoke([HumanMessage(content=prompt)])
    return {**state, "answer": response.content, "retry_count": retry_count + 1}

# ── Node 4: Evaluate ───────────────────────────────────────────────
def evaluate_node(state: AgentState) -> AgentState:
    # Only evaluate when we used retrieval
    if state["route"] != "retrieve" or not state["context"]:
        return {**state, "eval_scores": {"faithfulness": 1.0, "answer_relevancy": 1.0}}

    scores = evaluate_answer(
        question=state["question"],
        answer=state["answer"],
        contexts=state["context"]
    )
    return {**state, "eval_scores": scores}

# ── Conditional edge: retry or finish ─────────────────────────────
def should_retry(state: AgentState) -> Literal["generate", "end"]:
    scores = state.get("eval_scores", {})
    faithfulness = scores.get("faithfulness", 1.0)
    relevancy = scores.get("answer_relevancy", 1.0)
    retry_count = state.get("retry_count", 0)

    if (faithfulness < 0.7 or relevancy < 0.7) and retry_count < 2:
        print(f"Score too low, retrying... (attempt {retry_count + 1})")
        return "generate"
    return "end"

# ── Conditional edge: where to go after router ─────────────────────
def route_decision(state: AgentState) -> Literal["retrieve", "generate"]:
    if state["route"] == "retrieve":
        return "retrieve"
    return "generate"

# ── Build the graph ────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("evaluate", evaluate_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        route_decision,
        {"retrieve": "retrieve", "generate": "generate"}
    )

    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "evaluate")

    # Retry loop or finish
    graph.add_conditional_edges(
        "evaluate",
        should_retry,
        {"generate": "generate", "end": END}
    )

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
        retry_count=0,
        eval_scores={}
    )

    result = graph.invoke(initial_state)

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "route": result["route"],
        "eval_scores": result.get("eval_scores", {}),
        "retry_count": result.get("retry_count", 0)
    }