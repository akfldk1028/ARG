"""
Customer Support Agent - A2A Protocol Server
Port: 9002
Framework: OpenAI Agents SDK (Triage Agent with handoffs)
"""
import os, sys, asyncio
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

import dotenv
dotenv.load_dotenv()

from agents import Agent, Runner
from models import UserAccountContext

app = FastAPI(title="Customer Support Agent A2A Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORT = 9002

# Simplified triage agent for A2A (without streamlit-dependent handoffs)
triage_agent = Agent(
    name="Customer Support Triage Agent",
    instructions="""You are a customer support agent. You help customers with their questions about:
- User Account (login, password, profile, security)
- Billing (payments, refunds, subscriptions, invoices)
- Orders (status, shipping, returns, tracking)
- Technical Support (bugs, errors, how-to, setup)

Classify the customer's issue and provide helpful assistance.
If the issue is off-topic, politely redirect them.
Be professional and concise.""",
)

default_context = UserAccountContext(
    customer_id=0,
    name="A2A User",
    tier="basic",
)


@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "description": "Customer support triage agent that classifies and handles account, billing, order, and technical support issues. Built with OpenAI Agents SDK.",
        "name": "customer-support-agent",
        "preferredTransport": "JSONRPC",
        "protocolVersion": "0.3.0",
        "skills": [
            {"id": "account-support", "name": "Account Support", "description": "Handle account-related issues"},
            {"id": "billing-support", "name": "Billing Support", "description": "Handle billing inquiries"},
            {"id": "order-support", "name": "Order Support", "description": "Handle order-related questions"},
            {"id": "technical-support", "name": "Technical Support", "description": "Handle technical issues"},
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
        result = await Runner.run(
            triage_agent,
            message_text,
            context=default_context,
        )
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
    print(f"=== Customer Support Agent A2A Server ===")
    print(f"Port: {PORT}")
    print(f"Agent Card: http://localhost:{PORT}/.well-known/agent-card.json")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
