#!/usr/bin/env python3
"""
Hook 2 - PostToolUse (Edit/Write/MultiEdit)
코드 작성 직후 Claude에게 rules 기준 자체 검증 및 수정 요청.
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


def main() -> None:
    """PostToolUse hook 진입점 - 코드 작성 후 Claude에게 rules 검증 요청"""
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input", {})

    file_path = tool_input.get("file_path", "")
    new_string = tool_input.get("new_string") or tool_input.get("content", "")
    cwd = data.get("cwd", os.getcwd())

    if not file_path or not new_string:
        sys.exit(0)

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
    if not rules_text:
        sys.exit(0)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"[WORKFLOW VALIDATION REQUEST]\n"
                f"방금 작성한 코드({file_path})가 WORKFLOW RULES를 위반하는지 검토하고, "
                f"위반 사항이 있으면 즉시 수정해주세요.\n"
                f"[/WORKFLOW VALIDATION REQUEST]"
            ),
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
