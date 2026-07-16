import streamlit as st
from pinecone import Pinecone
from groq import Groq

# ══════════════════════════════════════════════════════════════════════════════
# 1. PAGE CONFIG  (must be the very first Streamlit call in the script)
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="SBP Regulatory Intelligence",
    page_icon="◈",
    layout="wide"
)

# ══════════════════════════════════════════════════════════════════════════════
# 2. CONFIGURATION & KEYS
# ══════════════════════════════════════════════════════════════════════════════
# Keys are read from Streamlit's secrets file instead of being hardcoded here -
# a plaintext key sitting in this .py file is the most common way keys leak.
#
# TO SET THIS UP:
#   1. In the SAME folder as this app.py, create a folder named exactly:
#        .streamlit
#   2. Inside it, create a file named exactly:
#        secrets.toml
#   3. Paste this into it, with your real keys in place of the example values:
#
#        PINECONE_API_KEY = "your-pinecone-key-here"
#        PINECONE_INDEX_NAME = "regulatory-circulars"
#        PINECONE_NAMESPACE = "circulars"
#        GROQ_API_KEY = "your-groq-key-here"
#
try:
    PINECONE_API_KEY = st.secrets["PINECONE_API_KEY"]
    PINECONE_INDEX_NAME = st.secrets.get("PINECONE_INDEX_NAME", "regulatory-circulars")
    PINECONE_NAMESPACE = st.secrets.get("PINECONE_NAMESPACE", "circulars")
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
except Exception:
    st.error(
        "Missing `.streamlit/secrets.toml`. Create that file in the same folder "
        "as app.py with your PINECONE_API_KEY, PINECONE_INDEX_NAME, "
        "PINECONE_NAMESPACE, and GROQ_API_KEY values - see the comment at the "
        "top of this file for the exact format."
    )
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# 3. DESIGN SYSTEM  -  sleek, minimal, warm-neutral with one accent hue
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Manrope:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --bg: #11151A;
        --surface: #1A1F26;
        --surface-hover: #212832;
        --text: #EDEFF3;
        --muted: #7C8790;
        --accent: #4FAE8C;
        --accent-soft: rgba(79, 174, 140, 0.12);
        --line: rgba(237, 239, 243, 0.08);
    }

    html, body, .stApp {
        background: var(--bg);
        color: var(--text);
    }

    .block-container {
        max-width: 760px;
        padding-top: 2.5rem;
        padding-bottom: 8rem;
    }

    /* ── Header ────────────────────────────────────────────────────────── */
    .app-header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 8px;
    }
    .app-mark {
        flex-shrink: 0;
        width: 40px;
        height: 40px;
        border-radius: 12px;
        background: var(--accent-soft);
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .app-header h1 {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        font-size: 1.45rem;
        color: var(--text);
        margin: 0;
        letter-spacing: -0.01em;
    }
    .app-subtitle {
        font-family: 'Manrope', sans-serif;
        font-size: 0.88rem;
        color: var(--muted);
        margin: 6px 0 30px 0;
    }

    /* ── Welcome / empty state ─────────────────────────────────────────── */
    @media (prefers-reduced-motion: no-preference) {
        .welcome-panel { animation: fadeUp 0.5s ease-out; }
    }
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .welcome-panel {
        padding: 6px 0 4px 0;
        margin-bottom: 6px;
    }
    .welcome-panel h2 {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        font-size: 1.75rem;
        color: var(--text);
        margin: 0 0 6px 0;
        letter-spacing: -0.01em;
    }
    .welcome-panel p {
        font-family: 'Manrope', sans-serif;
        font-size: 0.95rem;
        color: var(--muted);
        margin: 0 0 22px 0;
        max-width: 480px;
    }

    /* Starter-question buttons (Streamlit st.button, restyled) */
    div[data-testid="stButton"] button {
        background: var(--surface) !important;
        border: 1px solid var(--line) !important;
        border-radius: 12px !important;
        color: var(--text) !important;
        font-family: 'Manrope', sans-serif !important;
        font-size: 0.87rem !important;
        text-align: left !important;
        padding: 14px 16px !important;
        height: auto !important;
        white-space: normal !important;
        transition: border-color 0.15s ease, transform 0.15s ease, background 0.15s ease !important;
    }
    div[data-testid="stButton"] button:hover {
        background: var(--surface-hover) !important;
        border-color: var(--accent) !important;
        transform: translateY(-1px);
    }
    div[data-testid="stButton"] button:focus-visible {
        outline: 2px solid var(--accent) !important;
        outline-offset: 2px;
    }

    /* ── Messages ──────────────────────────────────────────────────────── */
    @media (prefers-reduced-motion: no-preference) {
        .msg-row { animation: fadeUp 0.3s ease-out; }
    }
    .msg-row {
        margin-bottom: 16px;
        font-family: 'Manrope', sans-serif;
    }
    .msg-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.66rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 6px;
        display: block;
        color: var(--muted);
    }
    .msg-user .msg-label { text-align: right; }

    .msg-bubble {
        padding: 13px 17px;
        border-radius: 14px;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .msg-user { margin-left: 14%; }
    .msg-user .msg-bubble {
        background: var(--accent-soft);
        border: 1px solid rgba(79, 174, 140, 0.25);
        color: var(--text);
    }
    .msg-assistant { margin-right: 6%; }
    .msg-assistant .msg-bubble {
        background: var(--surface);
        border: 1px solid var(--line);
        color: var(--text);
    }

    /* ── Citations ─────────────────────────────────────────────────────── */
    .citation-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 10px;
        margin-right: 6%;
    }
    .citation-chip {
        display: flex;
        align-items: center;
        gap: 7px;
        padding: 6px 11px;
        border-radius: 8px;
        background: var(--surface);
        border: 1px solid var(--line);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: var(--muted);
        transition: border-color 0.15s ease;
    }
    .citation-chip:hover { border-color: var(--accent); }
    .citation-ref { color: var(--text); font-weight: 500; }
    .citation-chip a {
        color: var(--accent);
        text-decoration: none;
    }
    .citation-chip a:hover { text-decoration: underline; }

    /* ── Streamlit chrome ──────────────────────────────────────────────── */
    [data-testid="stChatInput"] textarea {
        background: var(--surface) !important;
        border: 1px solid var(--line) !important;
        border-radius: 14px !important;
        color: var(--text) !important;
        font-family: 'Manrope', sans-serif !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 1px var(--accent) !important;
    }
    [data-testid="stSpinner"] p {
        font-family: 'Manrope', sans-serif;
        color: var(--accent);
    }
    </style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 4. INITIALIZE CONNECTIONS
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def init_services():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index_host = pc.describe_index(PINECONE_INDEX_NAME).host
    index = pc.Index(host=index_host)

    # Initialize Groq AI client
    groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
    return index, groq_client

try:
    index, groq_client = init_services()
except Exception as e:
    st.error(f"Error initializing services: {e}")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# 5. INTELLIGENT RETRIEVAL & REASONING PIPELINE  (unchanged logic)
# ══════════════════════════════════════════════════════════════════════════════
def generate_intelligent_answer(user_query):
    # 1. Search Pinecone
    results = index.search(
        namespace=PINECONE_NAMESPACE,
        query={"inputs": {"text": user_query}, "top_k": 10},
        fields=["circular_number", "publication_date", "source_url", "chunk_text"]
    )
    
    hits = results.get("result", {}).get("hits", [])
    if not hits:
        return "No relevant regulatory documents found matching your query.", []
    
    # 2. Sort by date (Newest first)
    sorted_hits = sorted(
        hits, 
        key=lambda x: x.get("fields", {}).get("publication_date", "0000-00-00"), 
        reverse=True
    )
    
    # 3. Build context
    context_blocks = []
    citations = []
    for idx, hit in enumerate(sorted_hits, 1):
        fields = hit.get("fields", {})
        ref = fields.get("circular_number", "Unspecified")
        date = fields.get("publication_date", "Unknown")
        text = fields.get("chunk_text", "")
        
        context_blocks.append(f"Document [{idx}] - Ref: {ref} | Date: {date}\nContent: {text}")
        citations.append({"ref": ref, "date": date, "url": fields.get("source_url", "#")})
        
    combined_context = "\n---\n".join(context_blocks)
    
    # 4. Updated System Prompt with strict constraints
    system_prompt = (
        "You are an expert compliance officer for the State Bank of Pakistan (SBP).\n"
        "Your task is to answer the user's question accurately using ONLY the provided regulatory documents.\n\n"
        "STRICT COMPLIANCE RULES:\n"
        "1. Prioritize the newest documents. If an older document conflicts with a newer document, always base your final rule on the newer document.\n"
        "2. Provide a concise, high-level summary covering the main concepts or sub-topics first. DO NOT ask clarifying questions before giving your initial answer.\n"
        "3. Never mention 'Category B' Exchange Companies as they have been eliminated by 2023 reforms.\n"
        "4. Always cite circular reference numbers (e.g., [Document 1]) in your answer.\n"
        "5. End your response with EXACTLY ONE specific follow-up question to help the user narrow down which sub-topic they want to explore next."
    )
    
    # 5. Call Groq
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Regulatory Documents:\n{combined_context}\n\nUser Question: {user_query}"}
            ],
            temperature=0.1 # Lower temperature for more factual consistency
        )
        return completion.choices[0].message.content, citations
    except Exception as e:
        return f"Error connecting to AI engine: {e}", []
# ══════════════════════════════════════════════════════════════════════════════
# 6. HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="app-header">
    <div class="app-mark">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z"
                  fill="#4FAE8C"/>
        </svg>
    </div>
    <h1>SBP Regulatory Intelligence</h1>
</div>
<p class="app-subtitle">Ask a compliance question, get an answer backed by real circulars.</p>
""", unsafe_allow_html=True)

# Session state to store conversation
if "messages" not in st.session_state:
    st.session_state.messages = []


def render_citations(citations):
    """Renders a row of citation chips for a list of citation dicts."""
    if not citations:
        return
    chips = "".join(
        f"<div class='citation-chip'>"
        f"<span class='citation-ref'>{c['ref']}</span>"
        f"<span>{c['date']}</span>"
        f"<a href='{c['url']}' target='_blank'>view &#8599;</a>"
        f"</div>"
        for c in citations
    )
    st.markdown(f"<div class='citation-row'>{chips}</div>", unsafe_allow_html=True)


# ── Starter questions, shown only before the first message ────────────────────
STARTER_PROMPTS = [
    {"icon": "&#8644;", "text": "What are the latest foreign exchange regulations?"},
    {"icon": "&#128200;", "text": "What is the current monetary policy rate?"},
    {"icon": "&#127960;", "text": "Any new Islamic banking circulars?"},
    {"icon": "&#128197;", "text": "What's the policy on bank holidays?"},
]

pending_query = None

if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-panel">
        <h2>Welcome. What are you looking into today?</h2>
        <p>Pick a starting point below, or type your own question - every
        answer is traced back to the actual SBP circular it came from.</p>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(2)
    for i, prompt in enumerate(STARTER_PROMPTS):
        with cols[i % 2]:
            label = f"{prompt['icon']}&nbsp;&nbsp;{prompt['text']}"
            if st.button(prompt["text"], key=f"starter_{i}", use_container_width=True):
                pending_query = prompt["text"]

# Display previous messages
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"<div class='msg-row msg-user'><span class='msg-label'>You</span>"
            f"<div class='msg-bubble'>{msg['content']}</div></div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div class='msg-row msg-assistant'><span class='msg-label'>Compliance AI</span>"
            f"<div class='msg-bubble'>{msg['content']}</div></div>",
            unsafe_allow_html=True
        )
        if "citations" in msg and msg["citations"]:
            render_citations(msg["citations"])

# Chat Input Field
typed_query = st.chat_input("Ask a compliance question...")
user_query = typed_query or pending_query

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.markdown(
        f"<div class='msg-row msg-user'><span class='msg-label'>You</span>"
        f"<div class='msg-bubble'>{user_query}</div></div>",
        unsafe_allow_html=True
    )

    with st.spinner("Searching the archive..."):
        answer, citations = generate_intelligent_answer(user_query)

    st.session_state.messages.append({"role": "assistant", "content": answer, "citations": citations})
    st.markdown(
        f"<div class='msg-row msg-assistant'><span class='msg-label'>Compliance AI</span>"
        f"<div class='msg-bubble'>{answer}</div></div>",
        unsafe_allow_html=True
    )
    render_citations(citations)

    if pending_query:
        st.rerun()
