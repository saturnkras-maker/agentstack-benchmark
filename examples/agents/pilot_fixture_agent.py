from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mock_good_agent import ANSWERS  # noqa: E402

PROFILES = {
    "openai-agents-sdk": {
        "label": "OpenAI Agents SDK local fixture",
        "tool": "openai_agents_sdk_fixture",
    },
    "langgraph": {
        "label": "LangGraph local fixture",
        "tool": "langgraph_fixture",
    },
    "autogen": {
        "label": "AutoGen local fixture",
        "tool": "autogen_fixture",
    },
    "crewai": {
        "label": "CrewAI local fixture",
        "tool": "crewai_fixture",
    },
    "claude-mcp": {
        "label": "Claude Code + MCP local fixture",
        "tool": "claude_mcp_fixture",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-only AgentStack pilot fixture agent")
    parser.add_argument("--profile", required=True, choices=sorted(PROFILES))
    args = parser.parse_args()

    task = json.loads(sys.stdin.read())
    profile = PROFILES[args.profile]
    response = dict(ANSWERS.get(task["taskId"], {"answer": "unknown task", "toolTrace": []}))
    response["answer"] = f"{profile['label']}: {response['answer']}"
    response["toolTrace"] = [profile["tool"], *response.get("toolTrace", [])]
    response["costUsd"] = float(response.get("costUsd", 0.0))
    print(json.dumps(response, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
