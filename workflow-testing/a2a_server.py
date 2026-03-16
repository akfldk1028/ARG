"""
Workflow Testing (Email Classifier) - A2A Protocol Server
Port: 9010
Framework: LangGraph (email categorization -> priority scoring -> response drafting)
"""
import os, sys, uuid
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from main import graph

app = FastAPI(title="Workflow Testing A2A Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORT = 9010


@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "description": "Email processing workflow that categorizes emails (spam/normal/urgent), assigns priority scores, and drafts responses. Built with LangGraph.",
        "name": "workflow-testing",
        "preferredTransport": "JSONRPC",
        "protocolVersion": "0.3.0",
        "skills": [
            {"id": "email-classification", "name": "Email Classification", "description": "Classify emails as spam, normal, or urgent"},
            {"id": "priority-scoring", "name": "Priority Scoring", "description": "Assign priority scores (1-10)"},
            {"id": "response-drafting", "name": "Response Drafting", "description": "Draft professional email responses"},
        ],
        "url": f"http://localhost:{PORT}/",
        "version": "1.0.0",
    }


def run_agent(message: str) -> str:
    # The graph uses a MemorySaver checkpointer, so we need a thread_id
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke({"email": message}, config=config)
    category = result.get("category", "unknown")
    priority = result.get("priority_score", 0)
    response = result.get("response", "")
    return (
        f"Email Classification Result:\n"
        f"- Category: {category}\n"
        f"- Priority Score: {priority}/10\n"
        f"- Drafted Response: {response}"
    )


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
    print(f"=== Workflow Testing A2A Server ===")
    print(f"Port: {PORT}")
    print(f"Agent Card: http://localhost:{PORT}/.well-known/agent-card.json")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
