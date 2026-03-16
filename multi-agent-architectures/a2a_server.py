"""
Multi-Agent Architectures - A2A Protocol Server
Port: 9005
Framework: LangGraph (supervisor with language-specific sub-agents)
"""
import os, sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from graph import graph

app = FastAPI(title="Multi-Agent Architectures A2A Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORT = 9005


@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "description": "Multi-agent supervisor that routes to language-specific customer support agents (Korean, Spanish, Greek). Built with LangGraph.",
        "name": "multi-agent-architectures",
        "preferredTransport": "JSONRPC",
        "protocolVersion": "0.3.0",
        "skills": [
            {"id": "korean-support", "name": "Korean Support", "description": "Customer support in Korean"},
            {"id": "spanish-support", "name": "Spanish Support", "description": "Customer support in Spanish"},
            {"id": "greek-support", "name": "Greek Support", "description": "Customer support in Greek"},
            {"id": "multilingual-routing", "name": "Multilingual Routing", "description": "Routes to appropriate language agent"},
        ],
        "url": f"http://localhost:{PORT}/",
        "version": "1.0.0",
    }


def run_agent(message: str) -> str:
    from langchain_core.messages import HumanMessage
    result = graph.invoke({"messages": [HumanMessage(content=message)]})
    messages = result.get("messages", [])
    if messages:
        last = messages[-1]
        return last.content if hasattr(last, "content") else str(last)
    return "No response generated."


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
    print(f"=== Multi-Agent Architectures A2A Server ===")
    print(f"Port: {PORT}")
    print(f"Agent Card: http://localhost:{PORT}/.well-known/agent-card.json")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
