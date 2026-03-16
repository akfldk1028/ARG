"""
ChatGPT Clone - A2A Protocol Server
Port: 9001
Framework: OpenAI Agents SDK (Runner + Agent with tools)
"""
import os, sys, asyncio
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

import dotenv
dotenv.load_dotenv()

from agents import Agent, Runner, WebSearchTool

app = FastAPI(title="ChatGPT Clone A2A Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORT = 9001

agent = Agent(
    name="ChatGPT Clone",
    instructions="""You are a helpful assistant.
You have access to web search. Use it when the user asks about current events or things you don't know.""",
    tools=[WebSearchTool()],
)


@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "description": "ChatGPT Clone agent with web search, file search, image generation, and code interpreter tools. Built with OpenAI Agents SDK.",
        "name": "chatgpt-clone",
        "preferredTransport": "JSONRPC",
        "protocolVersion": "0.3.0",
        "skills": [
            {"id": "web-search", "name": "Web Search", "description": "Search the web for information"},
            {"id": "general-chat", "name": "General Chat", "description": "General purpose assistant"},
        ],
        "url": f"http://localhost:{PORT}/",
        "version": "1.0.0",
    }


def run_agent(message: str) -> str:
    result = asyncio.get_event_loop().run_until_complete(
        Runner.run(agent, message)
    )
    return result.final_output


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
    print(f"=== ChatGPT Clone A2A Server ===")
    print(f"Port: {PORT}")
    print(f"Agent Card: http://localhost:{PORT}/.well-known/agent-card.json")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
