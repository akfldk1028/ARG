"""
Job Hunter Agent - A2A Protocol Server
Port: 9007
Framework: CrewAI (JobHunterCrew with search, matching, resume optimization, interview prep)
"""
import os, sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

import dotenv
dotenv.load_dotenv()

app = FastAPI(title="Job Hunter Agent A2A Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORT = 9007


@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "description": "Job hunting agent that searches for jobs, matches them to your resume, optimizes your resume, researches companies, and prepares interview questions. Built with CrewAI.",
        "name": "job-hunter-agent",
        "preferredTransport": "JSONRPC",
        "protocolVersion": "0.3.0",
        "skills": [
            {"id": "job-search", "name": "Job Search", "description": "Search for job listings"},
            {"id": "resume-matching", "name": "Resume Matching", "description": "Match jobs to resume"},
            {"id": "resume-optimization", "name": "Resume Optimization", "description": "Optimize resume for specific jobs"},
            {"id": "interview-prep", "name": "Interview Prep", "description": "Prepare interview questions and tips"},
        ],
        "url": f"http://localhost:{PORT}/",
        "version": "1.0.0",
    }


def run_agent(message: str) -> str:
    from main import JobHunterCrew

    # Parse level, position, location from message
    # Default values if not parseable
    level = "Senior"
    position = message
    location = "Remote"

    # Try to extract structured info
    msg_lower = message.lower()
    for lvl in ["junior", "mid", "senior", "lead", "principal", "staff"]:
        if lvl in msg_lower:
            level = lvl.capitalize()
            break

    # Try to extract location after "in" keyword
    if " in " in msg_lower:
        parts = message.split(" in ")
        if len(parts) >= 2:
            location = parts[-1].strip()
            position = parts[0].strip()

    result = (
        JobHunterCrew()
        .crew()
        .kickoff(
            inputs={
                "level": level,
                "position": position,
                "location": location,
            }
        )
    )

    # Collect all task outputs
    output_parts = []
    for task_output in result.tasks_output:
        if task_output.pydantic:
            output_parts.append(str(task_output.pydantic))
        elif task_output.raw:
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
    print(f"=== Job Hunter Agent A2A Server ===")
    print(f"Port: {PORT}")
    print(f"Agent Card: http://localhost:{PORT}/.well-known/agent-card.json")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
