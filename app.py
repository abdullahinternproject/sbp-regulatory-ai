import os
import uuid
import streamlit as st
from groq import Groq
from pinecone import Pinecone
from streamlit_local_storage import LocalStorage

# ══════════════════════════════════════════════════════════════════════════════
# 1. PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="SBP Regulatory Intelligence", page_icon="◈", layout="wide"
)

# ══════════════════════════════════════════════════════════════════════════════
# 2. CONFIGURATION & KEYS
# ══════════════════════════════════════════════════════════════════════════════
try:
  PINECONE_API_KEY = st.secrets["PINECONE_API_KEY"]
  PINECONE_INDEX_NAME = st.secrets.get(
      "PINECONE_INDEX_NAME", "regulatory-circulars"
  )
  PINECONE_NAMESPACE = st.secrets.get("PINECONE_NAMESPACE", "circulars")
  GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
except Exception:
  st.error(
      "Missing `.streamlit/secrets.toml`. Create that file in the same folder "
      "with your PINECONE_API_KEY, PINECONE_INDEX_NAME, PINECONE_NAMESPACE, "
      "and GROQ_API_KEY values."
  )
  st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# 3. DESIGN SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
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

    /* ── Messages ──────────────────────────────────────────────────────── */
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
    }
    .citation-ref { color: var(--text); font-weight: 500; }
    .citation-chip a { color: var(--accent); text-decoration: none; }

    [data-testid="stChatInput"] textarea {
        background: var(--surface) !important;
        border: 1px solid var(--line) !important;
        border-radius: 14px !important;
        color: var(--text) !important;
        font-family: 'Manrope', sans-serif !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# 4. INITIALIZE CONNECTIONS & LOCAL STORAGE
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def init_services():
  pc = Pinecone(api_key=PINECONE_API_KEY)
  index_host = pc.describe_index(PINECONE_INDEX_NAME).host
  index = pc.Index(host=index_host)
  groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
  return index, groq_client

try:
  index, groq_client = init_services()
except Exception as e:
  st.error(f"Error initializing services: {e}")
  st.stop()

# Initialize Local Storage Manager
localS = LocalStorage()

# ══════════════════════════════════════════════════════════════════════════════
# 5. RETRIEVAL & REASONING PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
def generate_intelligent_answer(user_query):
  results = index.search(
      namespace=PINECONE_NAMESPACE,
      query={"inputs": {"text": user_query}, "top_k": 10},
      fields=["circular_number", "publication_date", "source_url", "chunk_text"],
  )

  hits = results.get("result", {}).get("hits", [])
  if not hits:
    return "No relevant regulatory documents found matching your query.", []

  sorted_hits = sorted(
      hits,
      key=lambda x: x.get("fields", {}).get("publication_date", "0000-00-00"),
      reverse=True,
  )

  context_blocks = []
  citations = []
  for idx, hit in enumerate(sorted_hits, 1):
    fields = hit.get("fields", {})
    ref = fields.get("circular_number", "Unspecified")
    date = fields.get("publication_date", "Unknown")
    text = fields.get("chunk_text", "")

    context_blocks.append(
        f"Document [{idx}] - Ref: {ref} | Date: {date}\nContent: {text}"
    )
    citations.append(
        {"ref": ref, "date": date, "url": fields.get("source_url", "#")}
    )

  combined_context = "\n---\n".join(context_blocks)

  system_prompt = (
      "You are an expert compliance officer and institutional guide for the"
      " State Bank of Pakistan (SBP).\n\n"
      "STRICT COMPLIANCE & ANSWERING RULES:\n"
      "1. REGULATORY QUERIES: Answer questions directly based on retrieved"
      " context. Do NOT insert literal text bracket references like '[Document"
      " 1]' or '[Document 2]' inside your text response, as citations are"
      " handled separately by the user interface.\n"
      "2. GENERAL / LEADERSHIP QUERIES: For questions about SBP leadership"
      " (e.g., Governor Jameel Ahmad), organizational structure, or official"
      " reports, rely on retrieved context or general official knowledge.\n"
      "3. RESPONSE STRUCTURE: Always deliver a clear, high-level summary first"
      " covering the key points. DO NOT ask clarifying questions before"
      " answering.\n"
      "4. FOLLOW-UP: End your response with EXACTLY ONE specific follow-up"
      " question to guide the user to the next logical topic."
  )

  if not groq_client:
    return (
        "**Demo mode:** add your free Groq API key to `.streamlit/secrets.toml`"
        " to generate AI answers.",
        citations,
    )

  try:
    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Regulatory Documents:\n{combined_context}\n\nUser Question:"
                    f" {user_query}"
                ),
            },
        ],
        temperature=0.1,
    )
    return completion.choices[0].message.content, citations
  except Exception as e:
    return f"Unable to generate response via Groq. Error: {e}", citations

# ══════════════════════════════════════════════════════════════════════════════
# 6. PERSISTENT BROWSER-LOCAL MULTI-CHAT MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
if "chats" not in st.session_state:
  saved_chats = localS.getItem("sbp_chats")
  if saved_chats and isinstance(saved_chats, dict):
    st.session_state.chats = saved_chats
  else:
    initial_id = str(uuid.uuid4())
    st.session_state.chats = {initial_id: {"title": "New Chat", "messages": []}}

if "current_chat_id" not in st.session_state:
  saved_current_id = localS.getItem("sbp_current_chat_id")
  if saved_current_id and saved_current_id in st.session_state.chats:
    st.session_state.current_chat_id = saved_current_id
  else:
    st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]

def persist_state():
  localS.setItem("sbp_chats", st.session_state.chats)
  localS.setItem("sbp_current_chat_id", st.session_state.current_chat_id)

with st.sidebar:
  st.title("SBP Circulars AI")
  if st.button("➕ New Chat", use_container_width=True):
    new_id = str(uuid.uuid4())
    st.session_state.chats[new_id] = {"title": "New Chat", "messages": []}
    st.session_state.current_chat_id = new_id
    persist_state()
    st.rerun()

  st.divider()
  st.subheader("Chat History")

  for chat_id, chat_data in reversed(list(st.session_state.chats.items())):
    title = chat_data.get("title", "New Chat")
    is_active = chat_id == st.session_state.current_chat_id

    if is_active:
      col1, col2 = st.columns([0.82, 0.18])
      with col1:
        st.button(
            f"💬 {title}",
            key=f"btn_{chat_id}",
            disabled=True,
            use_container_width=True,
        )
      with col2:
        if st.button("🗑️", key=f"del_{chat_id}"):
          del st.session_state.chats[chat_id]

          if st.session_state.chats:
            st.session_state.current_chat_id = list(
                st.session_state.chats.keys()
            )[-1]
          else:
            fresh_id = str(uuid.uuid4())
            st.session_state.chats[fresh_id] = {
                "title": "New Chat",
                "messages": [],
            }
            st.session_state.current_chat_id = fresh_id
          persist_state()
          st.rerun()
    else:
      if st.button(title, key=f"btn_{chat_id}", use_container_width=True):
        st.session_state.current_chat_id = chat_id
        persist_state()
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 7. MAIN UI & CHAT INTERFACE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

def render_citations(citations):
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

current_id = st.session_state.current_chat_id
current_messages = st.session_state.chats[current_id]["messages"]

STARTER_PROMPTS = [
    {"icon": "&#8644;", "text": "What are the latest foreign exchange regulations?"},
    {"icon": "&#128200;", "text": "What is the current monetary policy rate?"},
    {"icon": "&#127960;", "text": "Any new Islamic banking circulars?"},
    {"icon": "&#128197;", "text": "What's the policy on bank holidays?"},
]

pending_query = None

if not current_messages:
  st.markdown(
      """
    <div class="welcome-panel">
        <h2>Welcome. What are you looking into today?</h2>
        <p>Pick a starting point below, or type your own question - every
        answer is traced back to the actual SBP circular it came from.</p>
    </div>
    """,
      unsafe_allow_html=True,
  )

  cols = st.columns(2)
  for i, prompt in enumerate(STARTER_PROMPTS):
    with cols[i % 2]:
      if st.button(
          prompt["text"], key=f"starter_{i}", use_container_width=True
      ):
        pending_query = prompt["text"]

for msg in current_messages:
  if msg["role"] == "user":
    st.markdown(
        f"<div class='msg-row msg-user'><span class='msg-label'>You</span>"
        f"<div class='msg-bubble'>{msg['content']}</div></div>",
        unsafe_allow_html=True,
    )
  else:
    st.markdown(
        "<div class='msg-row msg-assistant'><span"
        " class='msg-label'>Compliance AI</span>"
        f"<div class='msg-bubble'>{msg['content']}</div></div>",
        unsafe_allow_html=True,
    )
    if "citations" in msg and msg["citations"]:
      render_citations(msg["citations"])

typed_query = st.chat_input("Ask a compliance question...")
user_query = typed_query or pending_query

if user_query:
  if not current_messages:
    short_title = (
        user_query[:22] + "..." if len(user_query) > 22 else user_query
    )
    st.session_state.chats[current_id]["title"] = short_title

  current_messages.append({"role": "user", "content": user_query})
  st.markdown(
      f"<div class='msg-row msg-user'><span class='msg-label'>You</span>"
      f"<div class='msg-bubble'>{user_query}</div></div>",
      unsafe_allow_html=True,
  )

  with st.spinner("Searching the archive..."):
    answer, citations = generate_intelligent_answer(user_query)

  current_messages.append(
      {"role": "assistant", "content": answer, "citations": citations}
  )
  persist_state()

  st.markdown(
      "<div class='msg-row msg-assistant'><span"
      " class='msg-label'>Compliance AI</span>"
      f"<div class='msg-bubble'>{answer}</div></div>",
      unsafe_allow_html=True,
  )
  render_citations(citations)

  if pending_query:
    st.rerun()
