#!/usr/bin/env python3
"""
Hook 2 - PostToolUse 클라이언트 스크립트 (Edit/Write/MultiEdit)

[역할]
Claude Code가 파일을 작성/수정한 직후 자동 실행됨.
작성된 파일 경로와 cwd를 FastAPI 서버에 전송하여 rules를 받아오고,
hookSpecificOutput.additionalContext JSON으로 Claude에게 재검토를 요청함.
Claude가 방금 작성한 코드를 rules 기준으로 자체 검증하는 이중 안전망 역할.

[동작 흐름]
  Claude Code (PostToolUse 이벤트 - Edit/Write/MultiEdit)
    → 이 스크립트 실행 (stdin으로 tool_input 등 전달)
    → FastAPI 서버에 POST /get_rules {cwd}
    → rules 존재 확인
    → hookSpecificOutput.additionalContext JSON stdout 출력
    → Claude Code가 additionalContext를 Claude 컨텍스트에 주입
    → Claude가 방금 작성한 코드를 재검토하여 위반 시 모드에 따라 처리

[WORKFLOW_MODE 환경변수]
  interactive (기본값): 위반 시 수정 제안만 함 (개발자가 직접 판단)
  ralph              : 위반 시 즉시 수정 (AI 자율 작업 파이프라인용)
  off                : rules 검증 완전 스킵 (레거시 코드 작업, 긴급 hotfix 등)

  설정 방법:
    - ~/.claude/settings.json의 env 블록에서 설정 (모든 세션 적용)
    - 터미널에서 export WORKFLOW_MODE=ralph (해당 세션만 적용)
    - Ralph 파이프라인 sh 스크립트에서 환경변수 주입 권장

[주의]
  - additionalContext JSON 포맷만 PostToolUse에서 동작함 (plain text 동작 안 함)
  - 별도 Anthropic API 키 불필요 (Claude 자체 검증)
  - 서버 연결 실패 시 경고만 출력하고 정상 종료 (Claude 작업 차단 안 함)
"""
import json
import os
import sys
import urllib.request
import urllib.error

# 팀 공용 서버 사용 시 환경변수로 URL 변경
SERVER_URL = os.environ.get("WORKFLOW_SERVER_URL", "http://192.168.214.152:27842")

# 동작 모드: interactive (기본) | ralph | off
WORKFLOW_MODE = os.environ.get("WORKFLOW_MODE", "interactive")


def main() -> None:
    """PostToolUse hook 진입점 - 코드 작성 후 Claude에게 rules 검증 요청"""
    # off 모드면 즉시 종료 (rules 검증 스킵)
    if WORKFLOW_MODE == "off":
        sys.exit(0)

    # Claude Code가 stdin으로 전달하는 JSON (tool_name, tool_input, cwd 등 포함)
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input", {})

    # 작성된 파일 경로와 변경 내용 추출
    file_path = tool_input.get("file_path", "")
    new_string = tool_input.get("new_string") or tool_input.get("content", "")
    cwd = data.get("cwd", os.getcwd())

    # 파일 경로나 변경 내용이 없으면 검증 불필요
    if not file_path or not new_string:
        sys.exit(0)

    # 서버에 cwd 전송 → rules 존재 여부 확인
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
        # 서버 연결 실패 시 경고만 출력하고 정상 종료 (Claude 작업 차단 안 함)
        print(f"[WORKFLOW] 서버 연결 실패 ({SERVER_URL}): {e}", file=sys.stderr)
        sys.exit(0)

    rules_text = result.get("rules_text", "")
    if not rules_text:
        # 적용할 rules가 없으면 검증 불필요
        sys.exit(0)

    # 모드에 따라 Claude에게 요청할 액션 결정
    if WORKFLOW_MODE == "ralph":
        action = "위반 사항이 있으면 즉시 수정해주세요."   # AI 자율 작업: 자동 수정
    else:
        action = "위반 사항이 있으면 수정 제안을 해주세요."  # Interactive: 제안만

    # hookSpecificOutput.additionalContext JSON 출력
    # → Claude Code가 이 JSON을 파싱하여 Claude 컨텍스트에 additionalContext를 주입
    # → Claude가 방금 작성한 코드를 재검토하도록 유도
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"[WORKFLOW VALIDATION REQUEST]\n"
                f"방금 작성한 코드({file_path})가 WORKFLOW RULES를 위반하는지 검토하고, "
                f"{action}\n"
                f"[/WORKFLOW VALIDATION REQUEST]"
            ),
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
