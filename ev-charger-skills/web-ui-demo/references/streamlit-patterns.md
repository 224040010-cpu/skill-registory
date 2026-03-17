# Streamlit Patterns Reference

Advanced patterns for building polished Streamlit demos.

## Complete Chat Application Template

```python
import streamlit as st
from datetime import datetime

# Page config - MUST be first Streamlit command
st.set_page_config(
    page_title="Cloud Agent Demo",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished aesthetics
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Space+Grotesk:wght@300;500;700&display=swap');

/* Global styles */
.stApp {
    font-family: 'Space Grotesk', sans-serif;
}

/* Chat container */
.stChatMessage {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
}

/* Remove default padding */
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* Custom header */
.main-header {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 2.5rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 1rem;
}

/* Status indicators */
.status-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
}

.status-online {
    background: rgba(34, 197, 94, 0.2);
    color: #22c55e;
}

.status-offline {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
}

section[data-testid="stSidebar"] .stMarkdown {
    color: #e2e8f0;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = f"demo-{datetime.now().strftime('%Y%m%d%H%M%S')}"

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    model = st.selectbox(
        "Model",
        ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"],
        index=0
    )
    
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    
    st.divider()
    
    st.markdown("### 📊 Session Info")
    st.markdown(f"**Session ID:** `{st.session_state.session_id[:8]}...`")
    st.markdown(f"**Messages:** {len(st.session_state.messages)}")
    
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Main content
st.markdown('<p class="main-header">⚡ Cloud Agent</p>', unsafe_allow_html=True)
st.markdown("EV Charger Support Assistant")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about EV chargers, error codes, troubleshooting..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Call your agent here
            # response = await agent.process_message(prompt, st.session_state.session_id)
            response = "This is where the agent response would appear."
        
        st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
```

## Streaming Response Pattern

```python
import streamlit as st

def stream_response(prompt):
    """Generator that yields response chunks."""
    # Replace with actual agent streaming
    import time
    words = "This is a streaming response from the agent...".split()
    for word in words:
        yield word + " "
        time.sleep(0.05)

# In chat handler
with st.chat_message("assistant"):
    response_placeholder = st.empty()
    full_response = ""
    
    for chunk in stream_response(prompt):
        full_response += chunk
        response_placeholder.markdown(full_response + "▌")
    
    response_placeholder.markdown(full_response)
```

## Multi-Column Layout

```python
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Chat")
    # Chat interface here

with col2:
    st.subheader("Device Info")
    
    with st.container(border=True):
        st.metric("Model", "DH480")
        st.metric("Serial", "SN12345678")
        st.metric("Firmware", "v2.1.3")
```

## Expandable Sections

```python
with st.expander("🔍 View Diagnosis Details", expanded=False):
    st.json({
        "root_cause": "Contactor failure",
        "confidence": 0.92,
        "matched_cases": ["CASE-1234", "CASE-5678"]
    })

with st.expander("📋 Generated Ticket"):
    st.code("""
Ticket ID: TKT-20240315-001
Priority: High
Category: Hardware - Contactor
    """)
```

## Tabs for Different Views

```python
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Analytics", "📚 Knowledge Base"])

with tab1:
    # Chat interface

with tab2:
    st.line_chart(data)
    
with tab3:
    st.dataframe(knowledge_df)
```

## Custom Components

### Status Card

```python
def status_card(title, value, status="normal"):
    colors = {
        "normal": "#22c55e",
        "warning": "#f59e0b", 
        "error": "#ef4444"
    }
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
        border-radius: 12px;
        padding: 1.5rem;
        border-left: 4px solid {colors[status]};
    ">
        <p style="color: #888; margin: 0; font-size: 0.875rem;">{title}</p>
        <p style="color: #fff; margin: 0.5rem 0 0 0; font-size: 1.5rem; font-weight: 600;">{value}</p>
    </div>
    """, unsafe_allow_html=True)
```

### Progress Steps

```python
def progress_steps(steps, current_step):
    st.markdown("""
    <style>
    .step-container { display: flex; justify-content: space-between; margin: 1rem 0; }
    .step { 
        flex: 1; 
        text-align: center; 
        padding: 1rem;
        position: relative;
    }
    .step::after {
        content: '';
        position: absolute;
        top: 50%;
        right: 0;
        width: 100%;
        height: 2px;
        background: #333;
        z-index: -1;
    }
    .step.active { color: #667eea; }
    .step.completed { color: #22c55e; }
    </style>
    """, unsafe_allow_html=True)
    
    cols = st.columns(len(steps))
    for i, (col, step) in enumerate(zip(cols, steps)):
        with col:
            status = "completed" if i < current_step else "active" if i == current_step else ""
            icon = "✓" if i < current_step else str(i + 1)
            st.markdown(f"**{icon}** {step}")
```

## File Upload Handling

```python
uploaded_file = st.file_uploader(
    "Upload log file",
    type=["log", "txt", "json"],
    help="Upload device logs for analysis"
)

if uploaded_file:
    content = uploaded_file.read().decode()
    with st.expander("📄 File Preview"):
        st.code(content[:1000] + "..." if len(content) > 1000 else content)
```

## Environment Variables

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Use secrets in production
api_key = os.getenv("ANTHROPIC_API_KEY") or st.secrets.get("ANTHROPIC_API_KEY")
```

## Running the App

```bash
# Development
streamlit run app.py --server.runOnSave true

# With custom port
streamlit run app.py --server.port 8080

# Production (disable dev features)
streamlit run app.py --server.fileWatcherType none --client.showErrorDetails false
```
