"""
News Reader Agent - A2A Protocol Server
Port: 9008
Framework: CrewAI (NewsReaderAgent crew with hunter, summarizer, curator)
"""
import os, sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

import dotenv
dotenv.load_dotenv()

app = FastAPI(title="News Reader Agent A2A Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORT = 9008


@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "description": "News reader agent that hunts for news, summarizes articles, and curates a final report on any topic. Built with CrewAI.",
        "name": "news-reader-agent",
        "preferredTransport": "JSONRPC",
        "protocolVersion": "0.3.0",
        "skills": [
            {"id": "news-hunting", "name": "News Hunting", "description": "Search and find news on a topic"},
            {"id": "summarization", "name": "Summarization", "description": "Summarize news articles"},
            {"id": "curation", "name": "News Curation", "description": "Curate and compile news reports"},
        ],
        "url": f"http://localhost:{PORT}/",
        "version": "1.0.0",
    }


def run_agent(message: str) -> str:
    from main import NewsReaderAgent

    result = NewsReaderAgent().crew().kickoff(inputs={"topic": message})

    output_parts = []
    for task_output in result.tasks_output:
        if task_output.raw:
            output_parts.append(task_output.raw)

    if output_parts:
        return "\n\n---\n\n".join(output_parts)
    return str(result)


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
    print(f"=== News Reader Agent A2A Server ===")
    print(f"Port: {PORT}")
    print(f"Agent Card: http://localhost:{PORT}/.well-known/agent-card.json")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
