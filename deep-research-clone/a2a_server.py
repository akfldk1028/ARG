"""
Deep Research Clone - A2A Protocol Server
Port: 9013
Framework: AutoGen (SelectorGroupChat with research planner, agent, analyst, reviewer)
Note: Extracted from notebook deep-research-team.ipynb
"""
import os, sys, asyncio
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

import dotenv
dotenv.load_dotenv()

app = FastAPI(title="Deep Research Clone A2A Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORT = 9013


def _build_team():
    """Build the AutoGen SelectorGroupChat team (extracted from notebook)."""
    from autogen_agentchat.teams import SelectorGroupChat
    from autogen_agentchat.agents import AssistantAgent
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
    from tools import web_search_tool, save_report_to_md

    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

    research_planner = AssistantAgent(
        "research_planner",
        description="A strategic research coordinator that breaks down complex questions into research subtasks",
        model_client=model_client,
        system_message="""You are a research planning specialist. Your job is to create a focused research plan.
For each research question, create a FOCUSED research plan with:
1. Core Topics: 2-3 main areas to investigate
2. Search Queries: Create 3-5 specific search queries
Keep the plan focused and achievable.""",
    )

    research_agent = AssistantAgent(
        "research_agent",
        description="A web research specialist that searches and extracts content",
        tools=[web_search_tool],
        model_client=model_client,
        system_message="""You are a web research specialist. Execute 3-5 searches from the research plan.
Extract key information: facts, statistics, developments, expert opinions.
After completing searches, summarize what you found.""",
    )

    research_analyst = AssistantAgent(
        "research_analyst",
        description="An expert analyst that creates research reports",
        model_client=model_client,
        system_message="""You are a research analyst. Create a comprehensive report with:
## Executive Summary
## Background & Current State
## Analysis & Insights
## Future Outlook
## Sources
End with "REPORT_COMPLETE" when finished.""",
    )

    quality_reviewer = AssistantAgent(
        "quality_reviewer",
        description="A quality assurance specialist that evaluates research completeness",
        tools=[save_report_to_md],
        model_client=model_client,
        system_message="""You are a quality reviewer. Check if the research analyst produced a complete report.
When you see a complete report ending with "REPORT_COMPLETE":
1. Save it using save_report_to_md
2. Say: "APPROVED"
If not complete, tell the analyst to finish.""",
    )

    research_enhancer = AssistantAgent(
        "research_enhancer",
        description="A specialist that identifies critical gaps only",
        model_client=model_client,
        system_message="""You are a research enhancement specialist. Only suggest additional searches if there are MAJOR gaps.
If research is sufficient, say: "The research is sufficient to proceed with the report."
Only suggest 1-2 searches if absolutely necessary.""",
    )

    selector_prompt = """Choose the best agent for the current task:
{roles}
Current conversation: {history}
WORKFLOW:
1. No planning yet -> research_planner
2. Planning done, no research -> research_agent
3. After research -> research_enhancer ONCE
4. If sufficient -> research_analyst
5. If REPORT_COMPLETE -> quality_reviewer
After 2 research_agent rounds max, proceed to research_analyst."""

    text_termination = TextMentionTermination("APPROVED")
    max_message_termination = MaxMessageTermination(max_messages=30)
    termination_condition = text_termination | max_message_termination

    team = SelectorGroupChat(
        participants=[
            research_agent,
            research_analyst,
            research_enhancer,
            research_planner,
            quality_reviewer,
        ],
        selector_prompt=selector_prompt,
        model_client=model_client,
        termination_condition=termination_condition,
    )
    return team


@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "description": "Deep research agent that plans research, searches the web, analyzes findings, and produces comprehensive research reports. Built with AutoGen SelectorGroupChat.",
        "name": "deep-research-clone",
        "preferredTransport": "JSONRPC",
        "protocolVersion": "0.3.0",
        "skills": [
            {"id": "research-planning", "name": "Research Planning", "description": "Break down research questions into subtasks"},
            {"id": "web-research", "name": "Web Research", "description": "Search and extract web content"},
            {"id": "report-writing", "name": "Report Writing", "description": "Write comprehensive research reports"},
        ],
        "url": f"http://localhost:{PORT}/",
        "version": "1.0.0",
    }


async def run_agent(message: str) -> str:
    team = _build_team()
    result = await team.run(task=message)

    # Extract the final messages
    output_parts = []
    for msg in result.messages:
        if hasattr(msg, "content") and msg.content:
            output_parts.append(msg.content)

    if output_parts:
        # Return the last substantial message (usually the report)
        for part in reversed(output_parts):
            if len(part) > 100:
                return part
        return output_parts[-1]
    return "Research completed but no output was generated."


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
    print(f"=== Deep Research Clone A2A Server ===")
    print(f"Port: {PORT}")
    print(f"Agent Card: http://localhost:{PORT}/.well-known/agent-card.json")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
