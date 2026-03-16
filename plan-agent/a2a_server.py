"""
Plan Agent - A2A Protocol Server
Port: 9018
Framework: Claude Code CLI with --permission-mode plan

Runs Claude Code CLI in plan mode to analyze codebases and generate
implementation plans without making changes. Returns structured plans
via A2A protocol.

Usage:
    python a2a_server.py
    # Agent Card: http://localhost:9018/.well-known/agent-card.json
"""

import os
import sys
import json
import subprocess
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import dotenv
dotenv.load_dotenv()

app = FastAPI(title="Plan Agent A2A Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PORT = 9018

# Default working directory for Claude CLI
DEFAULT_WORK_DIR = os.getenv("PLAN_AGENT_WORK_DIR", "D:/Data/25_ACE")


@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "description": (
            "Plan Agent that uses Claude Code CLI in plan mode "
            "(--permission-mode plan) to analyze codebases and generate "
            "implementation plans. Does NOT modify files."
        ),
        "name": "plan-agent",
        "preferredTransport": "JSONRPC",
        "protocolVersion": "0.3.0",
        "skills": [
            {
                "id": "plan",
                "name": "Implementation Planning",
                "description": (
                    "Analyze a codebase and generate an implementation plan. "
                    "Uses Claude Code CLI in plan mode (read-only)."
                ),
            },
            {
                "id": "analyze",
                "name": "Code Analysis",
                "description": (
                    "Analyze code structure, architecture, and provide insights. "
                    "Read-only operation."
                ),
            },
            {
                "id": "review",
                "name": "Code Review",
                "description": (
                    "Review code changes and provide feedback. "
                    "Does not modify any files."
                ),
            },
        ],
        "url": f"http://localhost:{PORT}/",
        "version": "1.0.0",
    }


def run_claude_plan(
    prompt: str,
    work_dir: Optional[str] = None,
    timeout: int = 300,
) -> dict:
    """
    Run Claude Code CLI in plan mode.

    Args:
        prompt: The planning/analysis task description
        work_dir: Directory to run Claude in (cwd)
        timeout: Max execution time in seconds

    Returns:
        dict with keys: success, output, error, execution_time_ms
    """
    import time
    start = time.time()

    cwd = work_dir or DEFAULT_WORK_DIR
    if not Path(cwd).exists():
        return {
            "success": False,
            "output": None,
            "error": f"Work directory does not exist: {cwd}",
            "execution_time_ms": 0,
        }

    # Build Claude CLI command
    cmd = [
        "claude",
        "-p", prompt,
        "--permission-mode", "plan",
        "--output-format", "json",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )

        elapsed_ms = int((time.time() - start) * 1000)

        if result.returncode != 0:
            return {
                "success": False,
                "output": result.stdout or None,
                "error": result.stderr or f"Exit code: {result.returncode}",
                "execution_time_ms": elapsed_ms,
            }

        # Parse JSON output from Claude CLI
        output = result.stdout.strip()
        try:
            parsed = json.loads(output)
            # Claude CLI JSON output has a "result" field with the text
            text_result = parsed.get("result", output)
        except json.JSONDecodeError:
            text_result = output

        return {
            "success": True,
            "output": text_result,
            "error": None,
            "execution_time_ms": elapsed_ms,
        }

    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "success": False,
            "output": None,
            "error": f"Claude CLI timed out after {timeout}s",
            "execution_time_ms": elapsed_ms,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "output": None,
            "error": (
                "Claude CLI not found. "
                "Install: npm install -g @anthropic-ai/claude-code"
            ),
            "execution_time_ms": 0,
        }
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "success": False,
            "output": None,
            "error": str(e),
            "execution_time_ms": elapsed_ms,
        }


def extract_request(body: dict) -> tuple[str, Optional[str]]:
    """
    Extract message text and optional work_dir from A2A request body.

    Supports two formats:
    1. Standard A2A: params.message.parts[].text
    2. Extended: params.message.metadata.work_dir for directory override

    Returns:
        (message_text, work_dir)
    """
    params = body.get("params", {})
    message = params.get("message", {})

    # Extract text from parts
    parts = message.get("parts", [])
    message_text = " ".join(
        p.get("text", "") for p in parts if "text" in p
    ).strip()

    # Extract optional work_dir from metadata
    metadata = message.get("metadata", {})
    work_dir = metadata.get("work_dir")

    return message_text, work_dir


@app.post("/")
async def handle_message(req: Request):
    """Handle A2A JSON-RPC 2.0 message."""
    body = await req.json()
    message_text, work_dir = extract_request(body)

    if not message_text:
        return {
            "id": body.get("id", "1"),
            "jsonrpc": "2.0",
            "result": {
                "kind": "message",
                "role": "agent",
                "parts": [{"kind": "text", "text": "No message provided."}],
            },
        }

    # Run Claude CLI in plan mode (blocking - runs in thread pool)
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: run_claude_plan(message_text, work_dir=work_dir),
    )

    # Format response
    if result["success"]:
        response_text = result["output"] or "Plan completed (no output)."
    else:
        response_text = f"Plan failed: {result['error']}"
        if result["output"]:
            response_text += f"\n\nPartial output:\n{result['output']}"

    return {
        "id": body.get("id", "1"),
        "jsonrpc": "2.0",
        "result": {
            "kind": "message",
            "role": "agent",
            "parts": [{"kind": "text", "text": response_text}],
            "metadata": {
                "success": result["success"],
                "execution_time_ms": result["execution_time_ms"],
                "mode": "plan",
            },
        },
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    # Verify Claude CLI is available
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        cli_available = result.returncode == 0
        cli_version = result.stdout.strip() if cli_available else None
    except Exception:
        cli_available = False
        cli_version = None

    return {
        "status": "healthy" if cli_available else "degraded",
        "cli_available": cli_available,
        "cli_version": cli_version,
        "work_dir": DEFAULT_WORK_DIR,
        "port": PORT,
    }


if __name__ == "__main__":
    print(f"=== Plan Agent A2A Server ===")
    print(f"Port: {PORT}")
    print(f"Work Dir: {DEFAULT_WORK_DIR}")
    print(f"Mode: Claude CLI --permission-mode plan (read-only)")
    print(f"Agent Card: http://localhost:{PORT}/.well-known/agent-card.json")
    print(f"Health: http://localhost:{PORT}/health")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
