"""
Hello LangGraph - A2A Protocol Server
Port: 9004
Framework: LangGraph (poem generator with human feedback)
"""
import os, sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState

# Build a simplified graph without human-in-the-loop interrupt
# (the original uses interrupt() which requires checkpointer + resume)
llm = init_chat_model("openai:gpt-4o-mini")


class State(MessagesState):
    pass


def chatbot(state: State) -> State:
    response = llm.invoke(
        f"""You are an expert at making poems.
You are given a topic and need to write a poem about it.
Write the poem directly without asking for feedback.

Here is the conversation history:
{state['messages']}"""
    )
    return {"messages": [response]}


graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile(name="mr_poet_a2a")

app = FastAPI(title="Hello LangGraph A2A Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORT = 9004


@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "description": "Poem generator agent that writes poems on any topic. Built with LangGraph.",
        "name": "hello-langgraph",
        "preferredTransport": "JSONRPC",
        "protocolVersion": "0.3.0",
        "skills": [
            {"id": "poem-writing", "name": "Poem Writing", "description": "Write poems on any given topic"},
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
    print(f"=== Hello LangGraph A2A Server ===")
    print(f"Port: {PORT}")
    print(f"Agent Card: http://localhost:{PORT}/.well-known/agent-card.json")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
