"""
Workflow Architectures (Document Summarizer) - A2A Protocol Server
Port: 9016
Framework: LangGraph (parallel chunk summarization -> final summary)
Note: Extracted from notebook main.ipynb
"""
import os, sys
from pathlib import Path
from typing import TypedDict, Annotated
from operator import add
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from langgraph.types import Send
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model

llm = init_chat_model("openai:gpt-4o")


class State(TypedDict):
    document: str
    final_summary: str
    summaries: Annotated[list[dict], add]


def summarize_p(args):
    paragraph = args["paragraph"]
    index = args["index"]
    response = llm.invoke(
        f"Write a 3-sentence summary for this paragraph: {paragraph}",
    )
    return {
        "summaries": [
            {
                "summary": response.content,
                "index": index,
            }
        ],
    }


def dispatch_summarizers(state: State):
    chunks = state["document"].split("\n\n")
    return [
        Send("summarize_p", {"paragraph": chunk, "index": index})
        for index, chunk in enumerate(chunks)
    ]


def final_summary(state: State):
    response = llm.invoke(
        f"Using the following summaries, give me a final comprehensive summary: {state['summaries']}"
    )
    return {
        "final_summary": response.content,
    }


graph_builder = StateGraph(State)
graph_builder.add_node("summarize_p", summarize_p)
graph_builder.add_node("final_summary", final_summary)
graph_builder.add_conditional_edges(START, dispatch_summarizers, ["summarize_p"])
graph_builder.add_edge("summarize_p", "final_summary")
graph_builder.add_edge("final_summary", END)

graph = graph_builder.compile()

app = FastAPI(title="Workflow Architectures A2A Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORT = 9016


@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "description": "Document summarization workflow that splits documents into chunks, summarizes each in parallel, and produces a final comprehensive summary. Built with LangGraph.",
        "name": "workflow-architectures",
        "preferredTransport": "JSONRPC",
        "protocolVersion": "0.3.0",
        "skills": [
            {"id": "document-summarization", "name": "Document Summarization", "description": "Summarize long documents using parallel chunk processing"},
            {"id": "text-analysis", "name": "Text Analysis", "description": "Analyze and extract key points from text"},
        ],
        "url": f"http://localhost:{PORT}/",
        "version": "1.0.0",
    }


def run_agent(message: str) -> str:
    result = graph.invoke({"document": message})
    return result.get("final_summary", "No summary generated.")


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
    print(f"=== Workflow Architectures A2A Server ===")
    print(f"Port: {PORT}")
    print(f"Agent Card: http://localhost:{PORT}/.well-known/agent-card.json")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
