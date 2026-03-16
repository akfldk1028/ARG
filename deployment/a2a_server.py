"""
Deployment Agent - A2A Protocol Server
Port: 9011
Framework: OpenAI Agents SDK (already FastAPI, adds A2A agent-card + JSON-RPC endpoint)
"""
import os, sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from agents import Agent, Runner

app = FastAPI(title="Deployment Agent A2A Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORT = 9011

agent = Agent(
    name="Assistant",
    instructions="You help users with their questions.",
)


@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "description": "General-purpose assistant agent deployed as a FastAPI service. Built with OpenAI Agents SDK.",
        "name": "deployment-agent",
        "preferredTransport": "JSONRPC",
        "protocolVersion": "0.3.0",
        "skills": [
            {"id": "general-assistant", "name": "General Assistant", "description": "Answer general questions and help with tasks"},
        ],
        "url": f"http://localhost:{PORT}/",
        "version": "1.0.0",
    }


@app.post("/")
async def handle_message(req: Request):
    body = await req.json()
    parts = body.get("params", {}).get("message", {}).get("parts", [])
    message_text = " ".join(p.get("text", "") for p in parts if "text" in p)

    try:
        result = await Runner.run(agent, message_text)
        response = result.final_output
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
    print(f"=== Deployment Agent A2A Server ===")
    print(f"Port: {PORT}")
    print(f"Agent Card: http://localhost:{PORT}/.well-known/agent-card.json")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
