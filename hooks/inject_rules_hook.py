#!/usr/bin/env python3
"""
Hook 1 - UserPromptSubmit
FastAPI 서버에 cwd를 보내 rules를 받아 프롬프트 앞에 자동 주입.
"""
import json
import os
import sys
import urllib.request
import urllib.error

SERVER_URL = os.environ.get("WORKFLOW_SERVER_URL", "http://localhost:8000")


def main():
    data = json.load(sys.stdin)
    cwd = data.get("cwd", os.getcwd())

    payload = json.dumps({"cwd": cwd}).encode()
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
