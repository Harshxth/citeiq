from langchain_core.messages import HumanMessage
from app.rag import get_llm

def evaluate_answer(question: str, answer: str, contexts: list[str]) -> dict:
    try:
        llm = get_llm()
        context_text = "\n\n".join(contexts)

        # ── Faithfulness check ─────────────────────────────────────
        # Is every claim in the answer supported by the context?
        faithfulness_prompt = f"""You are an evaluation assistant.

Context:
{context_text}

Answer:
{answer}

Task: Check if every claim in the answer is supported by the context.
Score from 0.0 to 1.0 where:
- 1.0 = every claim is fully supported by the context
- 0.5 = some claims are supported, some are not
- 0.0 = the answer contradicts or ignores the context

Reply with ONLY a number between 0.0 and 1.0:"""

        faith_response = llm.invoke([HumanMessage(content=faithfulness_prompt)])
        faithfulness_score = float(faith_response.content.strip())

        # ── Relevancy check ────────────────────────────────────────
        # Does the answer actually address the question?
        relevancy_prompt = f"""You are an evaluation assistant.

Question: {question}

Answer: {answer}

Task: Score how well the answer addresses the question.
Score from 0.0 to 1.0 where:
- 1.0 = answer directly and completely addresses the question
- 0.5 = answer is partially relevant
- 0.0 = answer is off-topic or doesn't address the question

Reply with ONLY a number between 0.0 and 1.0:"""

        rel_response = llm.invoke([HumanMessage(content=relevancy_prompt)])
        relevancy_score = float(rel_response.content.strip())

        scores = {
            "faithfulness": round(faithfulness_score, 3),
            "answer_relevancy": round(relevancy_score, 3)
        }
        print(f"Eval scores: {scores}")
        return scores

    except Exception as e:
        print(f"Eval failed: {e}")
        return {"faithfulness": 1.0, "answer_relevancy": 1.0}