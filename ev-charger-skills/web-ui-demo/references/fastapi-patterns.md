# FastAPI Patterns Reference

Advanced patterns for building web UIs with FastAPI.

## Complete Chat Application Template

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import asyncio
from typing import Optional

app = FastAPI(
    title="Cloud Agent API",
    description="EV Charger Support Agent",
    version="1.0.0"
)

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    device_info: Optional[dict] = None

class ChatResponse(BaseModel):
    message: str
    response_type: str
    confidence: float
    suggestions: list[str] = []

# REST endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message and return response."""
    # Call your agent
    response = await agent.process_message(
        request.message,
        request.session_id or "default",
        request.device_info
    )
    return ChatResponse(
        message=response.message,
        response_type=response.response_type,
        confidence=response.confidence,
        suggestions=response.suggestions
    )

# WebSocket for streaming
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            
            # Stream response
            async for chunk in agent.stream(request["message"]):
                await websocket.send_text(json.dumps({
                    "type": "chunk",
                    "content": chunk
                }))
            
            await websocket.send_text(json.dumps({"type": "done"}))
    except WebSocketDisconnect:
        pass

# Embedded HTML UI
@app.get("/", response_class=HTMLResponse)
async def chat_ui():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cloud Agent</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Space+Grotesk:wght@300;500;700&display=swap" rel="stylesheet">
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Space Grotesk', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
            min-height: 100vh;
            color: #e2e8f0;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        header {
            text-align: center;
            margin-bottom: 2rem;
        }
        
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        
        .subtitle {
            color: #64748b;
            font-size: 1rem;
        }
        
        .chat-container {
            flex: 1;
            background: rgba(30, 41, 59, 0.5);
            border: 1px solid #334155;
            border-radius: 16px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .messages {
            flex: 1;
            padding: 1.5rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        
        .message {
            max-width: 80%;
            padding: 1rem 1.25rem;
            border-radius: 12px;
            font-size: 0.95rem;
            line-height: 1.5;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            align-self: flex-end;
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
        }
        
        .message.assistant {
            align-self: flex-start;
            background: #1e293b;
            border: 1px solid #334155;
        }
        
        .message.assistant pre {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 0.75rem;
            margin: 0.5rem 0;
            overflow-x: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
        }
        
        .input-area {
            padding: 1rem;
            border-top: 1px solid #334155;
            display: flex;
            gap: 0.75rem;
        }
        
        input {
            flex: 1;
            padding: 0.875rem 1rem;
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 10px;
            color: #e2e8f0;
            font-family: inherit;
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
        }
        
        input:focus {
            border-color: #3b82f6;
        }
        
        input::placeholder {
            color: #64748b;
        }
        
        button {
            padding: 0.875rem 1.5rem;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            border: none;
            border-radius: 10px;
            color: white;
            font-family: inherit;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        button:hover {
            filter: brightness(1.1);
            transform: translateY(-1px);
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .typing-indicator {
            display: flex;
            gap: 4px;
            padding: 1rem;
        }
        
        .typing-indicator span {
            width: 8px;
            height: 8px;
            background: #64748b;
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out both;
        }
        
        .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
        .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
        
        .examples {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            padding: 1rem;
            border-top: 1px solid #334155;
        }
        
        .example-btn {
            padding: 0.5rem 0.75rem;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            color: #94a3b8;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .example-btn:hover {
            background: #334155;
            color: #e2e8f0;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚡ Cloud Agent</h1>
            <p class="subtitle">EV Charger Support Assistant</p>
        </header>
        
        <div class="chat-container">
            <div class="messages" id="messages"></div>
            
            <div class="examples">
                <button class="example-btn" onclick="sendExample(this)">What does error 0x1234 mean?</button>
                <button class="example-btn" onclick="sendExample(this)">My charger screen is black</button>
                <button class="example-btn" onclick="sendExample(this)">BMW iX compatibility?</button>
            </div>
            
            <div class="input-area">
                <input type="text" id="input" placeholder="Ask about EV chargers..." 
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <button onclick="sendMessage()" id="send-btn">Send</button>
            </div>
        </div>
    </div>
    
    <script>
        const messagesEl = document.getElementById('messages');
        const inputEl = document.getElementById('input');
        const sendBtn = document.getElementById('send-btn');
        
        // WebSocket connection
        let ws = null;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat`);
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'chunk') {
                    updateLastMessage(data.content);
                } else if (data.type === 'done') {
                    sendBtn.disabled = false;
                    inputEl.disabled = false;
                }
            };
            
            ws.onclose = () => {
                setTimeout(connectWebSocket, 1000);
            };
        }
        
        connectWebSocket();
        
        function addMessage(content, role) {
            const div = document.createElement('div');
            div.className = `message ${role}`;
            div.innerHTML = content;
            messagesEl.appendChild(div);
            messagesEl.scrollTop = messagesEl.scrollHeight;
            return div;
        }
        
        function updateLastMessage(content) {
            const messages = messagesEl.querySelectorAll('.message.assistant');
            const last = messages[messages.length - 1];
            if (last) {
                last.innerHTML = content;
                messagesEl.scrollTop = messagesEl.scrollHeight;
            }
        }
        
        async function sendMessage() {
            const message = inputEl.value.trim();
            if (!message) return;
            
            inputEl.value = '';
            addMessage(message, 'user');
            addMessage('<div class="typing-indicator"><span></span><span></span><span></span></div>', 'assistant');
            
            sendBtn.disabled = true;
            inputEl.disabled = true;
            
            // Use WebSocket for streaming
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ message }));
            } else {
                // Fallback to REST
                try {
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message })
                    });
                    const data = await response.json();
                    updateLastMessage(data.message);
                } catch (error) {
                    updateLastMessage('Error: ' + error.message);
                }
                sendBtn.disabled = false;
                inputEl.disabled = false;
            }
        }
        
        function sendExample(btn) {
            inputEl.value = btn.textContent;
            sendMessage();
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Server-Sent Events (SSE) Alternative

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

@app.get("/api/stream")
async def stream_response(message: str):
    async def generate():
        async for chunk in agent.stream(message):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

## Static Files & Templates

```python
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
```

## CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Health Check & Metrics

```python
from datetime import datetime

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/metrics")
async def metrics():
    return {
        "total_requests": request_counter,
        "active_sessions": len(sessions),
        "avg_response_time_ms": avg_response_time
    }
```

## Running

```bash
# Development with auto-reload
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Production with workers
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4

# With SSL
uvicorn app:app --ssl-keyfile key.pem --ssl-certfile cert.pem
```

## Swagger UI

FastAPI automatically generates interactive API docs at:
- `/docs` - Swagger UI
- `/redoc` - ReDoc alternative
