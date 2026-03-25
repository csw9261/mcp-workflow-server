#!/usr/bin/env python3
"""
Hook 1 - UserPromptSubmit
로컬에서 .workflow.yaml을 읽어 team/project를 추출하고 서버에 전송.
"""
import json
import os
import sys
import urllib.request
import urllib.error

try:
    import yaml
except ImportError:
    yaml = None

SERVER_URL = os.environ.get("WORKFLOW_SERVER_URL", "http://localhost:8000")


def read_workflow_yaml(cwd: str) -> dict:
    """로컬 .workflow.yaml에서 team/project 추출"""
    if yaml is None:
        return {}
    workflow_path = os.path.join(cwd, ".workflow.yaml")
    if not os.path.exists(workflow_path):
        return {}
    with open(workflow_path) as f:
        config = yaml.safe_load(f) or {}
    return {
        "team": config.get("team"),
        "project": config.get("project"),
    }


def main():
    data = json.load(sys.stdin)
    cwd = data.get("cwd", os.getcwd())

    context = read_workflow_yaml(cwd)

    payload = json.dumps({
        "team": context.get("team"),
        "project": context.get("project"),
    }).encode()

    req = urllib.request.Request(
        f"{SERVER_URL}/get_rules",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
    except urllib.error.URLError as e:
        print(f"[WORKFLOW] 서버 연결 실패 ({SERVER_URL}): {e}", file=sys.stderr)
        sys.exit(0)

    rules_text = result.get("rules_text", "")
    applied = result.get("applied", [])

    if rules_text:
        context_text = f"[WORKFLOW RULES - 적용: {', '.join(applied)}]\n{rules_text}\n[/WORKFLOW RULES]"
        print(context_text)

    sys.exit(0)


if __name__ == "__main__":
    main()
