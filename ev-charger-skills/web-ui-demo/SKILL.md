---
name: web-ui-demo
description: Build beautiful demo web UIs for AI agents and applications. Use this skill when users mention "demo UI", "web interface", "test UI", "frontend demo", "chat interface", "Streamlit", "Gradio", "FastAPI UI", "interactive demo", or need to showcase an agent/API with a visual interface. Also triggers on "make it look good", "beautiful UI", "modern design", or requests to avoid generic AI aesthetics.
---

# Web UI Demo Builder

Build polished, distinctive demo interfaces for AI agents and applications.

## Quick Start Decision

| Need | Framework | When to Use |
|------|-----------|-------------|
| **Fastest path** | Streamlit | Chat demos, dashboards, single-page apps |
| **Pre-built chat UI** | Gradio | LLM demos, ML interfaces, shareable links |
| **Production-ready** | FastAPI + HTML | REST APIs, multi-endpoint services |
| **Maximum control** | React/Vue | Complex interactions, custom components |

**Default choice**: Streamlit for quick demos, FastAPI for existing Python backends.

## Framework Selection

### Streamlit (Recommended for Quick Demos)

```bash
pip install streamlit
```

Best for:
- Chat interfaces with `st.chat_message`
- Real-time streaming responses
- Quick prototypes with state management
- Internal demos and testing

### Gradio (Best for Shareable ML Demos)

```bash
pip install gradio
```

Best for:
- One-liner sharable public links
- Pre-built components (chat, audio, image)
- Hugging Face Spaces deployment
- Zero frontend code needed

### FastAPI + HTML (Best for Production)

Already common in Python projects. Best for:
- REST API endpoints with Swagger UI
- Custom frontend requirements
- WebSocket streaming
- Existing backend integration

## Frontend Aesthetics

Claude tends toward generic "AI slop" aesthetics. Apply these principles to create distinctive, polished UIs:

### Typography

**Never use**: Inter, Roboto, Open Sans, Arial, system fonts

**High-impact choices**:
- Code aesthetic: JetBrains Mono, Fira Code, Space Grotesk
- Editorial: Playfair Display, Crimson Pro, Fraunces
- Startup: Clash Display, Satoshi, Cabinet Grotesk
- Technical: IBM Plex family, Source Sans 3
- Distinctive: Bricolage Grotesque, Newsreader

**Key principle**: Use extremes - weight 100/200 vs 800/900 (not 400 vs 600). Size jumps 3x+ (not 1.5x).

### Color & Theme

- Commit to a cohesive aesthetic with CSS variables
- Dominant colors + sharp accents beat evenly-distributed palettes
- Draw from IDE themes (Dracula, Nord, Solarized) for inspiration
- Vary between light/dark themes across projects

**Avoid**: Purple gradients on white backgrounds (the #1 AI cliché)

### Motion & Animation

- Focus on high-impact moments: page load with staggered reveals
- Use CSS-only solutions for HTML, Motion library for React
- One well-orchestrated animation > scattered micro-interactions
- Apply `animation-delay` for staggered effects

### Backgrounds

- Create atmosphere and depth, never default to solid colors
- Layer CSS gradients for richness
- Use geometric patterns or contextual effects
- Match background treatment to overall aesthetic

## Implementation Patterns

### Pattern 1: Streamlit Chat Demo

```python
import streamlit as st

st.set_page_config(page_title="Agent Demo", page_icon="🤖", layout="wide")

# Custom CSS for better aesthetics
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Space+Grotesk:wght@300;500;700&display=swap');

.stApp {
    font-family: 'Space Grotesk', sans-serif;
}
.stChatMessage {
    font-family: 'JetBrains Mono', monospace;
}
</style>
""", unsafe_allow_html=True)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask something..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        # Call your agent here
        response = "Agent response goes here"
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
```

### Pattern 2: Gradio Chat with Streaming

```python
import gradio as gr

def respond(message, history):
    # Call your agent and yield for streaming
    response = ""
    for chunk in agent.stream(message):
        response += chunk
        yield response

demo = gr.ChatInterface(
    respond,
    title="🤖 Cloud Agent Demo",
    description="Ask me anything about EV chargers",
    theme=gr.themes.Soft(
        primary_hue="emerald",
        font=gr.themes.GoogleFont("Space Grotesk")
    ),
    examples=["What does error code 0x1234 mean?", "My charger shows a black screen"],
)

demo.launch()
```

### Pattern 3: FastAPI with Embedded Chat

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Cloud Agent API")

@app.get("/", response_class=HTMLResponse)
async def chat_ui():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cloud Agent</title>
        <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap" rel="stylesheet">
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: 'Space Grotesk', sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                min-height: 100vh;
                color: #eee;
            }
            /* Add more styling... */
        </style>
    </head>
    <body>
        <!-- Chat interface HTML -->
    </body>
    </html>
    """

@app.post("/api/chat")
async def chat(message: str):
    # Call your agent
    response = await agent.process_message(message, session_id="demo")
    return {"response": response.message}
```

## Common Pitfalls to Avoid

1. **Generic purple gradients** - Choose unexpected color combinations
2. **System fonts everywhere** - Pick one distinctive font, use it decisively
3. **Flat solid backgrounds** - Add depth with gradients or patterns
4. **Missing loading states** - Add skeleton loaders or spinners
5. **No streaming** - Always stream long responses for better UX
6. **Ignoring mobile** - Test responsive layouts

## Reference Files

| File | Contents |
|------|----------|
| `references/streamlit-patterns.md` | Advanced Streamlit components and layouts |
| `references/gradio-patterns.md` | Gradio theming and custom components |
| `references/fastapi-patterns.md` | FastAPI WebSocket streaming and static files |
| `references/css-aesthetics.md` | Full CSS prompt and theme examples |

## Quick Commands

```bash
# Streamlit
streamlit run app.py --server.port 8501

# Gradio
python app.py  # Opens browser automatically

# FastAPI
uvicorn app:app --reload --port 8000
```

## Demo Best Practices

1. **One-file scaffolds** - Start with everything in one file, extract later
2. **Safe defaults** - Include error handling and graceful degradation
3. **Streaming responses** - For snappy UX with LLMs
4. **Proper caching** - Avoid redundant API calls
5. **Honest limitations** - Show model uncertainty, don't oversell

Great demos feel like "tiny products" — snappy, legible, and honest about limitations.
