"""
Financial Analyst - A2A Protocol Server
Port: 9012
Framework: Google ADK (FinancialAdvisor agent with sub-agents)
"""
import os, sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

import dotenv
dotenv.load_dotenv()

app = FastAPI(title="Financial Analyst A2A Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORT = 9012

# Try to use Google ADK's native to_a2a() if available, otherwise wrap manually
_adk_app = None

def _try_adk_native():
    """Attempt to use Google ADK's native A2A support."""
    global _adk_app
    try:
        from financial_advisor.agent import financial_advisor
        from google.adk.a2a import to_a2a
        _adk_app = to_a2a(financial_advisor)
        return True
    except (ImportError, AttributeError):
        return False

_use_native_adk = _try_adk_native()


@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "description": "Financial advisor agent with data analysis, financial analysis, and news analysis sub-agents. Provides investment advice and reports. Built with Google ADK.",
        "name": "financial-analyst",
        "preferredTransport": "JSONRPC",
        "protocolVersion": "0.3.0",
        "skills": [
            {"id": "data-analysis", "name": "Data Analysis", "description": "Analyze financial data and trends"},
            {"id": "financial-analysis", "name": "Financial Analysis", "description": "Perform fundamental/technical analysis"},
            {"id": "news-analysis", "name": "News Analysis", "description": "Analyze financial news impact"},
            {"id": "investment-advice", "name": "Investment Advice", "description": "Provide investment recommendations"},
        ],
        "url": f"http://localhost:{PORT}/",
        "version": "1.0.0",
    }


async def run_agent(message: str) -> str:
    """Run the financial advisor agent using Google ADK InMemoryRunner."""
    from financial_advisor.agent import financial_advisor
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    runner = InMemoryRunner(agent=financial_advisor, app_name="financial_analyst_a2a")
    session = await runner.session_service.create_session(
        app_name="financial_analyst_a2a", user_id="a2a_user"
    )

    user_content = types.Content(
        parts=[types.Part(text=message)],
        role="user",
    )

    response_parts = []
    async for event in runner.run(
        user_id="a2a_user",
        session_id=session.id,
        new_message=user_content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_parts.append(part.text)

    return "\n".join(response_parts) if response_parts else "No response generated."


@app.post("/")
async def handle_message(req: Request):
    body = await req.json()
    parts = body.get("params", {}).get("message", {}).get("parts", [])
    message_text = " ".join(p.get("text", "") for p in parts if "text" in p)

    try:
        response = await run_agent(message_text)
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
    print(f"=== Financial Analyst A2A Server ===")
    print(f"Port: {PORT}")
    if _use_native_adk:
        print("Using native Google ADK A2A support")
    else:
        print("Using manual A2A wrapper with InMemoryRunner")
    print(f"Agent Card: http://localhost:{PORT}/.well-known/agent-card.json")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
