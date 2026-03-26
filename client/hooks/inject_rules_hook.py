#!/usr/bin/env python3
"""
Hook 1 - UserPromptSubmit 클라이언트 스크립트

[역할]
Claude Code가 프롬프트를 전송하기 직전에 자동 실행됨.
현재 작업 디렉토리(cwd)를 FastAPI 서버에 전송하여 rules를 받아오고,
plain text로 stdout에 출력 → Claude 컨텍스트에 자동 주입됨.

[동작 흐름]
  Claude Code (UserPromptSubmit 이벤트)
    → 이 스크립트 실행 (stdin으로 cwd 등 전달)
    → FastAPI 서버에 POST /get_rules {cwd}
    → 서버가 .workflow.yaml 감지 → global/team/project rules 병합 후 반환
    → plain text stdout 출력
    → Claude 컨텍스트에 주입됨

[설정]
  WORKFLOW_SERVER_URL: FastAPI 서버 주소 (기본값: http://localhost:27842)
    - 팀 공용 서버 사용 시: ~/.claude/settings.json의 env 블록에 설정
    - 예: "WORKFLOW_SERVER_URL": "http://team-server:27842"

[주의]
  - additionalContext JSON 포맷은 UserPromptSubmit에서 동작 안 함
  - plain text stdout만 동작함 (확인 완료)
  - 서버 연결 실패 시 경고만 출력하고 정상 종료 (Claude 작업 차단 안 함)
"""
import json
import os
import sys
import urllib.request
import urllib.error

# 팀 공용 서버 사용 시 환경변수로 URL 변경
# ~/.claude/settings.json의 env 블록에서 설정 가능
SERVER_URL = os.environ.get("WORKFLOW_SERVER_URL", "http://192.168.214.152:27842")


def main() -> None:
    """UserPromptSubmit hook 진입점 - rules를 서버에서 받아 Claude 컨텍스트에 주입"""
    # Claude Code가 stdin으로 전달하는 JSON (cwd, session_id 등 포함)
    data = json.load(sys.stdin)
    cwd = data.get("cwd", os.getcwd())

    # 서버에 cwd 전송 → 서버가 .workflow.yaml 읽어서 team/project 감지
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

    rules_text = result.get("rules_text", "")   # 포맷된 rules 텍스트
    applied = result.get("applied", [])          # 적용된 계층 목록 (project/team/global)

    if rules_text:
        # plain text로 stdout 출력 → Claude Code가 Claude 컨텍스트에 자동 주입
        context_text = f"[WORKFLOW RULES - 적용: {', '.join(applied)}]\n{rules_text}\n[/WORKFLOW RULES]"
        print(context_text)

    sys.exit(0)


if __name__ == "__main__":
    main()
