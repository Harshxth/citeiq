import streamlit as st
import requests
import base64

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="CiteIQ",
    page_icon="🏥",
    layout="wide"
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .score-good { color: #27500A; background: #EAF3DE; padding: 3px 10px; border-radius: 20px; font-size: 13px; }
    .score-mid  { color: #633806; background: #FAEEDA; padding: 3px 10px; border-radius: 20px; font-size: 13px; }
    .score-bad  { color: #791F1F; background: #FCEBEB; padding: 3px 10px; border-radius: 20px; font-size: 13px; }
    .source-tag {
        background: #E6F1FB; color: #0C447C;
        padding: 4px 10px; border-radius: 4px;
        font-size: 12px; margin-right: 6px;
        display: inline-block; margin-top: 4px;
    }
    .route-tag { color: #888; font-size: 12px; margin-top: 6px; }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_queries" not in st.session_state:
    st.session_state.total_queries = 0
if "total_retries" not in st.session_state:
    st.session_state.total_retries = 0
if "faith_scores" not in st.session_state:
    st.session_state.faith_scores = []

# ── Layout ─────────────────────────────────────────────────────────
sidebar, main = st.columns([1, 2.5])

with sidebar:
    st.markdown("## CiteIQ")
    st.caption("Clinical knowledge assistant")
    st.divider()

    st.markdown("#### Knowledge base")
    uploaded_files = st.file_uploader(
        "Upload documents",
        accept_multiple_files=True,
        type=["pdf", "txt"],
        label_visibility="collapsed"
    )

    if uploaded_files and st.button("Index documents", use_container_width=True):
        with st.spinner("Indexing..."):
            for file in uploaded_files:
                try:
                    content_b64 = base64.b64encode(file.read()).decode("utf-8")
                    response = requests.post(
                        f"{API_URL}/ingest",
                        json={"filename": file.name, "content_b64": content_b64},
                        timeout=120
                    )
                    if response.status_code == 200:
                        st.success(f"Indexed {file.name}")
                    else:
                        st.error(f"Failed: {response.text}")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()

    st.markdown("#### Session metrics")
    col1, col2 = st.columns(2)
    col1.metric("Queries", st.session_state.total_queries)
    col2.metric("Retries", st.session_state.total_retries)

    avg_faith = (
        round(sum(st.session_state.faith_scores) / len(st.session_state.faith_scores), 2)
        if st.session_state.faith_scores else "-"
    )
    st.metric("Avg faithfulness", avg_faith)

with main:
    st.markdown("#### Ask CiteIQ")

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.write(msg["content"])

                scores = msg.get("eval_scores", {})
                if scores:
                    faith = scores.get("faithfulness", 0)
                    rel = scores.get("answer_relevancy", 0)

                    def score_class(v):
                        return "score-good" if v >= 0.8 else "score-mid" if v >= 0.6 else "score-bad"

                    st.markdown(
                        f'<span class="{score_class(faith)}">Faithfulness {faith}</span> '
                        f'<span class="{score_class(rel)}">Relevancy {rel}</span>',
                        unsafe_allow_html=True
                    )

                sources = msg.get("sources", [])
                if sources:
                    tags = "".join([f'<span class="source-tag">{s}</span>' for s in sources])
                    st.markdown(tags, unsafe_allow_html=True)

                route = msg.get("route", "")
                retries = msg.get("retry_count", 0)
                if route:
                    st.markdown(
                        f'<div class="route-tag">Routed via {route} · {retries} retries</div>',
                        unsafe_allow_html=True
                    )

    question = st.chat_input("Ask a clinical question...")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        st.session_state.total_queries += 1

        with st.spinner("Searching knowledge base..."):
            try:
                response = requests.post(
                    f"{API_URL}/query",
                    json={"question": question},
                    timeout=120
                )
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": data["answer"],
                        "sources": data.get("sources", []),
                        "eval_scores": data.get("eval_scores", {}),
                        "route": data.get("route", ""),
                        "retry_count": data.get("retry_count", 0)
                    })
                    faith = data.get("eval_scores", {}).get("faithfulness")
                    if faith:
                        st.session_state.faith_scores.append(faith)
                    st.session_state.total_retries += data.get("retry_count", 0)
                else:
                    st.error("Query failed — check API logs")
            except Exception as e:
                st.error(f"Connection error: {e}")

        st.rerun()