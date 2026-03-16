"""
Content Pipeline Agent - A2A Protocol Server
Port: 9006
Framework: CrewAI Flow (ContentPipelineFlow with research, writing, SEO/virality scoring)
"""
import os, sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

import dotenv
dotenv.load_dotenv()

app = FastAPI(title="Content Pipeline Agent A2A Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORT = 9006


@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "description": "Content pipeline agent that researches topics, generates blog posts/tweets/LinkedIn posts, and scores them for SEO or virality. Built with CrewAI Flow.",
        "name": "content-pipeline-agent",
        "preferredTransport": "JSONRPC",
        "protocolVersion": "0.3.0",
        "skills": [
            {"id": "blog-writing", "name": "Blog Writing", "description": "Write SEO-optimized blog posts"},
            {"id": "tweet-writing", "name": "Tweet Writing", "description": "Write viral tweets"},
            {"id": "linkedin-writing", "name": "LinkedIn Writing", "description": "Write engaging LinkedIn posts"},
        ],
        "url": f"http://localhost:{PORT}/",
        "version": "1.0.0",
    }


def run_agent(message: str) -> str:
    from main import ContentPipelineFlow

    # Parse content_type from message, default to blog
    message_lower = message.lower()
    if "tweet" in message_lower:
        content_type = "tweet"
    elif "linkedin" in message_lower:
        content_type = "linkedin"
    else:
        content_type = "blog"

    # Extract topic: remove content type keywords
    topic = message
    for keyword in ["tweet", "linkedin", "blog", "write", "create", "make", "about", "a ", "an "]:
        topic = topic.replace(keyword, "").replace(keyword.capitalize(), "")
    topic = topic.strip()
    if not topic:
        topic = message

    flow = ContentPipelineFlow()
    result = flow.kickoff(
        inputs={
            "content_type": content_type,
            "topic": topic,
        }
    )

    if result is not None:
        if hasattr(result, "model_dump_json"):
            return result.model_dump_json(indent=2)
        return str(result)
    return f"Content pipeline completed for topic: {topic} (type: {content_type})"


@app.post("/")
async def handle_message(req: Request):
    body = await req.json()
    parts = body.get("params", {}).get("message", {}).get("parts", [])
    message_text = " ".join(p.get("text", "") for p in parts if "text" in p)

    try:
        response = run_agent(message_text)
    except Exception as e:
        response = f"Error: {str(e)}"

    return {
        "id": body.get("id", "1"),
        "jsonrpc": "2.0",
        "result": {
            "kind": "message",
            "role": "agent",
            "parts": [{"kind": "text", "text": response}],
        },
    }


if __name__ == "__main__":
    print(f"=== Content Pipeline Agent A2A Server ===")
    print(f"Port: {PORT}")
    print(f"Agent Card: http://localhost:{PORT}/.well-known/agent-card.json")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
