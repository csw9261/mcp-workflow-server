#!/usr/bin/env python3
"""
Hook 2 - PostToolUse (Edit/Write/MultiEdit)
FastAPI 서버에 변경된 코드를 보내 위반 여부를 검증.
"""
import json
import os
import sys
import urllib.request
import urllib.error

SERVER_URL = os.environ.get("WORKFLOW_SERVER_URL", "http://localhost:8000")


def main():
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input", {})

    file_path = tool_input.get("file_path", "")
    new_string = tool_input.get("new_string") or tool_input.get("content", "")
    cwd = data.get("cwd", os.getcwd())

    if not file_path or not new_string:
        sys.exit(0)

    if not os.path.exists(file_path):
        sys.exit(0)

    with open(file_path) as f:
        full_code = f.read()

    payload = json.dumps({
        "cwd": cwd,
        "file_path": file_path,
        "new_string": new_string,
        "full_code": full_code,
    }).encode()

    req = urllib.request.Request(
        f"{SERVER_URL}/validate_code",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
    except urllib.error.URLError as e:
        print(f"[WORKFLOW] 서버 연결 실패 ({SERVER_URL}): {e}", file=sys.stderr)
        sys.exit(0)

    violations = result.get("violations", [])
    if violations:
        print("[RULE VIOLATION DETECTED]")
        print("작성된 코드에서 다음 규칙 위반이 발견됐습니다:")
        for v in violations:
            line_info = f" (line {v['line']})" if v.get("line") else ""
            print(f"- [{v['id']}] {v['description']}{line_info} [출처: {v.get('source', 'unknown')}]")

    sys.exit(0)


if __name__ == "__main__":
    main()
