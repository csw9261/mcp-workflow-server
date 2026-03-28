"""
FastAPI 서버 - rules 제공 API
팀원들의 Hook 스크립트가 team/project를 로컬에서 감지 후 이 서버에 HTTP 요청을 보냄.
"""
import os
import sys
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

# server/ 디렉토리를 sys.path에 추가해 rule_engine 패키지를 임포트 가능하게 함
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rule_engine.loader import load_rules
from rule_engine.merger import merge_rules

app = FastAPI(title="mcp-workflow-server")


class GetRulesRequest(BaseModel):
    team: str | None = None     # 팀 식별자 (예: "backend")
    project: str | None = None  # 프로젝트 식별자 (예: "api-service")


class GetRulesResponse(BaseModel):
    applied: list[str]  # 실제로 적용된 컨텍스트 레이어 목록 (project, team, global 순)
    rules: list[dict]   # 병합된 rule 객체 목록
    rules_text: str     # 클라이언트가 바로 출력할 수 있는 plain text 형식의 rules


def _format_rules(rules: list) -> str:
    """rules 목록을 plain text로 포맷"""
    lines = []
    for r in rules:
        severity = r.get("severity", "error").upper()  # severity 없으면 ERROR로 기본값 처리
        lines.append(f"- [{r['id']}] [{severity}] {r['description']}")
    return "\n".join(lines)


@app.post("/get_rules", response_model=GetRulesResponse)
def get_rules(req: GetRulesRequest) -> GetRulesResponse:
    """team/project 기반으로 rules를 로드하여 반환"""
    context = {"team": req.team, "project": req.project}
    raw_rules = load_rules(context)   # 컨텍스트에 맞는 rule 파일들을 로드
    merged = merge_rules(raw_rules)   # 중복 제거 및 우선순위 적용 후 병합

    # 적용된 컨텍스트 레이어를 좁은 범위(project) → 넓은 범위(global) 순으로 기록
    applied = []
    if context.get("project"):
        applied.append(f"project={context['project']}")
    if context.get("team"):
        applied.append(f"team={context['team']}")
    applied.append("global")  # global은 항상 포함

    return GetRulesResponse(
        applied=applied,
        rules=merged,
        rules_text=_format_rules(merged),
    )


@app.get("/health")
def health() -> dict:
    """서버 상태 확인"""
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 27842))  # 환경변수 PORT가 없으면 기본 포트 27842 사용
    uvicorn.run("api_server:app", host="0.0.0.0", port=port, reload=False)
