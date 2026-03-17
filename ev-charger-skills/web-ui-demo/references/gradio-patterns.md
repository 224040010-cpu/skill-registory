# Gradio Patterns Reference

Advanced patterns for building polished Gradio demos.

## Complete Chat Application Template

```python
import gradio as gr
from typing import Generator

# Custom theme
custom_theme = gr.themes.Soft(
    primary_hue="emerald",
    secondary_hue="slate",
    neutral_hue="slate",
    font=gr.themes.GoogleFont("Space Grotesk"),
    font_mono=gr.themes.GoogleFont("JetBrains Mono"),
).set(
    body_background_fill="linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
    body_background_fill_dark="linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
    block_background_fill="#1e293b",
    block_background_fill_dark="#1e293b",
    block_border_color="#334155",
    block_label_text_color="#94a3b8",
    input_background_fill="#0f172a",
    input_border_color="#334155",
    button_primary_background_fill="linear-gradient(135deg, #10b981 0%, #059669 100%)",
    button_primary_text_color="#ffffff",
)

def respond(message: str, history: list) -> Generator[str, None, None]:
    """
    Chat response generator with streaming.
    
    Args:
        message: User's input message
        history: List of (user_msg, assistant_msg) tuples
    
    Yields:
        Partial response strings for streaming
    """
    # Call your agent here
    response = ""
    
    # Simulate streaming (replace with actual agent)
    import time
    words = f"Processing your query about: {message}".split()
    for word in words:
        response += word + " "
        time.sleep(0.05)
        yield response

# Create the interface
demo = gr.ChatInterface(
    fn=respond,
    title="⚡ Cloud Agent",
    description="EV Charger Support Assistant - Ask about error codes, troubleshooting, or compatibility",
    theme=custom_theme,
    examples=[
        "What does error code 0x1234 mean?",
        "My charger screen is black",
        "Is BMW iX compatible with DH480?",
        "The charging stops at 80%"
    ],
    retry_btn="🔄 Retry",
    undo_btn="↩️ Undo",
    clear_btn="🗑️ Clear",
    submit_btn="Send ➤",
)

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False  # Set True for public link
    )
```

## Custom Blocks Layout

```python
import gradio as gr

with gr.Blocks(theme=custom_theme, css=custom_css) as demo:
    gr.Markdown("# ⚡ Cloud Agent Demo")
    
    with gr.Row():
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                label="Chat",
                height=500,
                show_label=False,
                avatar_images=(None, "🤖")
            )
            
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Ask about EV chargers...",
                    show_label=False,
                    scale=4
                )
                submit = gr.Button("Send", variant="primary", scale=1)
        
        with gr.Column(scale=1):
            gr.Markdown("### 📊 Device Info")
            
            model_dd = gr.Dropdown(
                choices=["DH480", "DH240", "DH600", "AC Ultra"],
                label="Charger Model",
                value="DH480"
            )
            
            serial = gr.Textbox(
                label="Serial Number",
                placeholder="Enter SN..."
            )
            
            gr.Markdown("### 📎 Attachments")
            file_upload = gr.File(
                label="Upload Logs",
                file_types=[".log", ".txt", ".json"]
            )
    
    # Event handlers
    def user_message(user_msg, history):
        return "", history + [[user_msg, None]]
    
    def bot_response(history, model, serial):
        user_msg = history[-1][0]
        # Call agent with context
        response = f"Analyzing {model} (SN: {serial or 'N/A'}): {user_msg}"
        history[-1][1] = response
        return history
    
    msg.submit(user_message, [msg, chatbot], [msg, chatbot]).then(
        bot_response, [chatbot, model_dd, serial], [chatbot]
    )
    submit.click(user_message, [msg, chatbot], [msg, chatbot]).then(
        bot_response, [chatbot, model_dd, serial], [chatbot]
    )
```

## Custom CSS

```python
custom_css = """
/* Chat message styling */
.message {
    font-family: 'JetBrains Mono', monospace !important;
}

/* User message */
.user {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
}

/* Bot message */
.bot {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%) !important;
    border: 1px solid #475569 !important;
}

/* Input field */
.gradio-textbox input {
    background: #0f172a !important;
    border: 1px solid #334155 !important;
    color: #e2e8f0 !important;
}

/* Primary button */
.primary {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    border: none !important;
}

.primary:hover {
    filter: brightness(1.1) !important;
    transform: translateY(-1px) !important;
}

/* Code blocks in chat */
.message pre {
    background: #0f172a !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    padding: 1rem !important;
}

/* Markdown tables */
.message table {
    border-collapse: collapse;
    width: 100%;
}

.message th, .message td {
    border: 1px solid #334155;
    padding: 0.5rem;
}
"""
```

## Streaming with Async

```python
import gradio as gr
import asyncio

async def async_respond(message: str, history: list):
    """Async streaming response."""
    response = ""
    
    # Async generator for streaming
    async for chunk in agent.stream_async(message):
        response += chunk
        yield response

demo = gr.ChatInterface(
    fn=async_respond,
    # ... other params
)

demo.queue()  # Required for async
demo.launch()
```

## Multi-Tab Interface

```python
with gr.Blocks() as demo:
    with gr.Tabs():
        with gr.TabItem("💬 Chat"):
            chatbot = gr.Chatbot()
            msg = gr.Textbox()
        
        with gr.TabItem("📊 Analytics"):
            gr.Markdown("## Failure Analytics")
            chart = gr.Plot()
            
        with gr.TabItem("📚 Knowledge Base"):
            search = gr.Textbox(label="Search")
            results = gr.Dataframe()
```

## Accordion Sections

```python
with gr.Blocks() as demo:
    with gr.Accordion("🔧 Advanced Settings", open=False):
        temperature = gr.Slider(0, 1, 0.7, label="Temperature")
        max_tokens = gr.Slider(100, 4000, 1000, label="Max Tokens")
    
    with gr.Accordion("📋 Diagnosis Details", open=False):
        diagnosis_json = gr.JSON(label="Raw Diagnosis")
```

## Progress Indicator

```python
import gradio as gr

def process_with_progress(file, progress=gr.Progress()):
    progress(0, desc="Starting...")
    
    # Step 1
    progress(0.3, desc="Parsing logs...")
    time.sleep(1)
    
    # Step 2
    progress(0.6, desc="Analyzing patterns...")
    time.sleep(1)
    
    # Step 3
    progress(0.9, desc="Generating report...")
    time.sleep(1)
    
    progress(1.0, desc="Complete!")
    return "Analysis complete"

with gr.Blocks() as demo:
    file = gr.File(label="Upload")
    output = gr.Textbox(label="Result")
    btn = gr.Button("Analyze")
    btn.click(process_with_progress, file, output)
```

## Authentication

```python
demo.launch(
    auth=("admin", "password"),  # Simple auth
    # OR
    auth=authenticate_user,  # Custom function
    auth_message="Please login to access the demo"
)
```

## Public Sharing

```python
# Generate a public URL (72 hours)
demo.launch(share=True)

# Output: Running on public URL: https://xxxxx.gradio.live
```

## Running

```bash
# Basic
python app.py

# With specific port
python -c "demo.launch(server_port=7860)"

# In Jupyter/Colab
demo.launch(inline=True)

# Behind proxy
demo.launch(server_name="0.0.0.0", root_path="/demo")
```
