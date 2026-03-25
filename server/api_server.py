"""
FastAPI 서버 - rules 제공 API
팀원들의 Hook 스크립트가 team/project를 로컬에서 감지 후 이 서버에 HTTP 요청을 보냄.
"""
import os
import sys
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rule_engine.loader import load_rules
from rule_engine.merger import merge_rules

app = FastAPI(title="mcp-workflow-server")


class GetRulesRequest(BaseModel):
    team: str | None = None
    project: str | None = None


class GetRulesResponse(BaseModel):
    applied: list[str]
    rules: list[dict]
    rules_text: str


def _format_rules(rules: list) -> str:
    """rules 목록을 plain text로 포맷"""
    lines = []
    for r in rules:
        severity = r.get("severity", "error").upper()
        lines.append(f"- [{r['id']}] [{severity}] {r['description']}")
    return "\n".join(lines)


@app.post("/get_rules", response_model=GetRulesResponse)
def get_rules(req: GetRulesRequest) -> GetRulesResponse:
    """team/project 기반으로 rules를 로드하여 반환"""
    context = {"team": req.team, "project": req.project}
    raw_rules = load_rules(context)
    merged = merge_rules(raw_rules)

    applied = []
    if context.get("project"):
        applied.append(f"project={context['project']}")
    if context.get("team"):
        applied.append(f"team={context['team']}")
    applied.append("global")

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
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api_server:app", host="0.0.0.0", port=port, reload=False)
