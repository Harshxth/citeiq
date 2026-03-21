import streamlit as st
import requests
import base64
import os

API_URL = "http://localhost:8000"
IS_HF = os.getenv("SPACE_ID") is not None

st.set_page_config(
    page_title="CiteIQ — Clinical Knowledge Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding: 0 !important; max-width: 100% !important;}
    section[data-testid="stSidebar"] {display: none;}

    .score-good {color:#27500A;background:#EAF3DE;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:500;}
    .score-mid  {color:#633806;background:#FAEEDA;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:500;}
    .score-bad  {color:#791F1F;background:#FCEBEB;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:500;}
    .source-tag {background:#E6F1FB;color:#0C447C;padding:3px 8px;border-radius:4px;font-size:11px;margin-right:5px;display:inline-block;margin-top:3px;}
    .route-tag  {color:#888;font-size:11px;margin-top:5px;}

    .sidebar-card {
        background: #042C53;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    .metric-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-top: 8px;
    }
    .metric-item {
        background: rgba(255,255,255,0.06);
        border-radius: 8px;
        padding: 10px 12px;
        border: 0.5px solid rgba(255,255,255,0.08);
    }
    .metric-label {color:#85B7EB;font-size:10px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;}
    .metric-val   {color:#fff;font-size:22px;font-weight:500;line-height:1.1;margin-top:2px;}
    .metric-sub   {color:#5DCAA5;font-size:10px;margin-top:2px;}
    .doc-item {
        display:flex;align-items:center;gap:8px;
        padding:7px 10px;
        background:rgba(255,255,255,0.05);
        border-radius:6px;
        border:0.5px solid rgba(255,255,255,0.08);
        margin-bottom:5px;
    }
    .doc-dot {width:6px;height:6px;border-radius:50%;background:#5DCAA5;flex-shrink:0;}
    .doc-name {color:#E6F1FB;font-size:12px;}
    .doc-meta {color:#85B7EB;font-size:10px;}
    .section-label {color:#85B7EB;font-size:10px;font-weight:500;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;}
    .ai-header {display:flex;align-items:center;gap:6px;margin-bottom:5px;}
    .ai-label {font-size:12px;font-weight:500;color:#888;}
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────
for key, val in [
    ("messages", []),
    ("total_queries", 0),
    ("total_retries", 0),
    ("faith_scores", []),
    ("indexed_docs", ["sepsis.txt", "diabetes.txt", "hypertension.txt"])
]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── Layout ─────────────────────────────────────────────────────────
left, right = st.columns([1, 2.8])

with left:
    # Logo
    st.markdown("""
    <div class="sidebar-card">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
            <div style="width:32px;height:32px;background:#185FA5;border-radius:8px;display:flex;align-items:center;justify-content:center">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M8 2v12M2 8h12" stroke="white" stroke-width="2" stroke-linecap="round"/>
                    <circle cx="8" cy="8" r="3" stroke="#85B7EB" stroke-width="1.5"/>
                </svg>
            </div>
            <div>
                <div style="color:white;font-size:18px;font-weight:500">CiteIQ</div>
                <div style="color:#85B7EB;font-size:11px">Clinical knowledge assistant</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Knowledge base
    st.markdown("""<div class="sidebar-card">
        <div class="section-label">Knowledge base</div>
    """, unsafe_allow_html=True)

    if IS_HF:
        st.info("Live demo uses pre-loaded clinical documents. Upload available in local deployment.", icon="ℹ️")
    else:
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
                            if file.name not in st.session_state.indexed_docs:
                                st.session_state.indexed_docs.append(file.name)
                        else:
                            st.error(f"Failed: {response.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")

    for doc in st.session_state.indexed_docs:
        st.markdown(f"""
        <div class="doc-item">
            <div class="doc-dot"></div>
            <div>
                <div class="doc-name">{doc}</div>
                <div class="doc-meta">indexed · ready</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Metrics
    avg_faith = round(
        sum(st.session_state.faith_scores) / len(st.session_state.faith_scores), 2
    ) if st.session_state.faith_scores else "—"

    st.markdown(f"""
    <div class="sidebar-card">
        <div class="section-label">Session metrics</div>
        <div class="metric-grid">
            <div class="metric-item">
                <div class="metric-label">Queries</div>
                <div class="metric-val">{st.session_state.total_queries}</div>
                <div class="metric-sub">this session</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Avg faith.</div>
                <div class="metric-val">{avg_faith}</div>
                <div class="metric-sub">{"above threshold" if isinstance(avg_faith, float) and avg_faith >= 0.7 else "—"}</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Docs</div>
                <div class="metric-val">{len(st.session_state.indexed_docs)}</div>
                <div class="metric-sub">indexed</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Retries</div>
                <div class="metric-val">{st.session_state.total_retries}</div>
                <div class="metric-sub">auto-corrected</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with right:
    # Header
    st.markdown("""
    <div style="padding:1.25rem 1.5rem;border-bottom:0.5px solid var(--color-border-tertiary);display:flex;justify-content:space-between;align-items:center">
        <div>
            <div style="font-size:16px;font-weight:500;color:var(--color-text-primary)">Ask CiteIQ</div>
            <div style="font-size:12px;color:var(--color-text-secondary);margin-top:2px">Answers grounded in your documents · sources cited with every response</div>
        </div>
        <div style="display:flex;align-items:center;gap:6px">
            <div style="width:7px;height:7px;border-radius:50%;background:#5DCAA5"></div>
            <div style="font-size:12px;color:var(--color-text-secondary)">Live</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Chat history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown("""<div class="ai-header">
                    <div class="ai-label">CiteIQ</div>
                </div>""", unsafe_allow_html=True)
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

    # Input
    question = st.chat_input("Ask a clinical question — e.g. what are the early signs of septic shock?")
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