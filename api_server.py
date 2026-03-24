"""
FastAPI 서버 - rules 제공 및 코드 검증 API
팀원들의 Hook 스크립트가 이 서버에 HTTP 요청을 보냄.
"""
import os
import sys
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rule_engine.context_resolver import resolve_context
from rule_engine.loader import load_rules
from rule_engine.merger import merge_rules
from rule_engine.validator import validate_code

app = FastAPI(title="mcp-workflow-server")


class GetRulesRequest(BaseModel):
    cwd: str


class GetRulesResponse(BaseModel):
    applied: list[str]
    rules: list[dict]
    rules_text: str


class ValidateRequest(BaseModel):
    cwd: str
    file_path: str
    new_string: str
    full_code: str


class ValidateResponse(BaseModel):
    violations: list[dict]


def _format_rules(rules: list) -> str:
    lines = []
    for r in rules:
        severity = r.get("severity", "error").upper()
        lines.append(f"- [{r['id']}] [{severity}] {r['description']}")
    return "\n".join(lines)


@app.post("/get_rules", response_model=GetRulesResponse)
def get_rules(req: GetRulesRequest) -> GetRulesResponse:
    """cwd 기반으로 rules를 로드하여 반환"""
    context = resolve_context(req.cwd)
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


@app.post("/validate_code", response_model=ValidateResponse)
def validate(req: ValidateRequest) -> ValidateResponse:
    """변경된 코드를 rules 기준으로 검증"""
    context = resolve_context(req.cwd)
    raw_rules = load_rules(context)
    merged = merge_rules(raw_rules)

    if not merged:
        return ValidateResponse(violations=[])

    violations = validate_code(req.full_code, req.new_string, merged)
    return ValidateResponse(violations=violations or [])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api_server:app", host="0.0.0.0", port=port, reload=False)
