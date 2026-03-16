"""
YouTube Thumbnail Maker - A2A Protocol Server
Port: 9009
Framework: LangGraph (video transcription -> summarization -> thumbnail generation)
Note: Simplified for A2A - takes a text summary/topic instead of a video file,
      generates thumbnail prompts and images.
"""
import os, sys, base64
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from openai import OpenAI

llm = init_chat_model("openai:gpt-4o-mini")


class ThumbnailState(TypedDict):
    topic: str
    thumbnail_prompt: str
    thumbnail_file: str


def generate_prompt(state: ThumbnailState):
    response = llm.invoke(
        f"""Based on this topic/summary, create a detailed visual prompt for a YouTube thumbnail.
Include main visual elements, color scheme, text overlay suggestions, and composition.

Topic: {state['topic']}"""
    )
    return {"thumbnail_prompt": response.content}


def generate_thumbnail(state: ThumbnailState):
    client = OpenAI()
    try:
        result = client.images.generate(
            model="gpt-image-1",
            prompt=state["thumbnail_prompt"],
            quality="low",
            size="auto",
        )
        image_bytes = base64.b64decode(result.data[0].b64_json)
        filename = "thumbnail_a2a.jpg"
        filepath = str(Path(__file__).parent / filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        return {"thumbnail_file": filepath}
    except Exception as e:
        return {"thumbnail_file": f"Error generating image: {str(e)}"}


graph_builder = StateGraph(ThumbnailState)
graph_builder.add_node("generate_prompt", generate_prompt)
graph_builder.add_node("generate_thumbnail", generate_thumbnail)
graph_builder.add_edge(START, "generate_prompt")
graph_builder.add_edge("generate_prompt", "generate_thumbnail")
graph_builder.add_edge("generate_thumbnail", END)

graph = graph_builder.compile(name="thumbnail_maker_a2a")

app = FastAPI(title="YouTube Thumbnail Maker A2A Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORT = 9009


@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "description": "YouTube thumbnail maker that generates thumbnail prompts and images from video topics/summaries. Built with LangGraph and OpenAI image generation.",
        "name": "youtube-thumbnail-maker",
        "preferredTransport": "JSONRPC",
        "protocolVersion": "0.3.0",
        "skills": [
            {"id": "thumbnail-generation", "name": "Thumbnail Generation", "description": "Generate YouTube thumbnail images from topics"},
            {"id": "prompt-design", "name": "Prompt Design", "description": "Design visual prompts for thumbnails"},
        ],
        "url": f"http://localhost:{PORT}/",
        "version": "1.0.0",
    }


def run_agent(message: str) -> str:
    result = graph.invoke({"topic": message})
    prompt = result.get("thumbnail_prompt", "")
    filepath = result.get("thumbnail_file", "")
    return f"Thumbnail Prompt:\n{prompt}\n\nGenerated file: {filepath}"


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
    print(f"=== YouTube Thumbnail Maker A2A Server ===")
    print(f"Port: {PORT}")
    print(f"Agent Card: http://localhost:{PORT}/.well-known/agent-card.json")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
