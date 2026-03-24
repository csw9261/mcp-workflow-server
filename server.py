from mcp.server.fastmcp import FastMCP
from rule_engine.context_resolver import resolve_context
from rule_engine.loader import load_rules
from rule_engine.merger import merge_rules
from rule_engine.validator import validate_code as _validate_code

mcp = FastMCP("workflow-server")


@mcp.tool()
def get_rules(cwd: str) -> dict:
    """cwd 기반으로 rules를 자동 감지하고 병합하여 반환"""
    context = resolve_context(cwd)
    raw_rules = load_rules(context)
    merged = merge_rules(raw_rules)
    return {
        "merged_rules": merged,
        "applied_context": context,
    }


@mcp.tool()
def validate_code(full_code: str, new_string: str | None, cwd: str) -> dict:
    """변경된 코드(new_string)를 전체 파일(full_code) 컨텍스트와 함께 검증"""
    context = resolve_context(cwd)
    raw_rules = load_rules(context)
    merged = merge_rules(raw_rules)
    violations = _validate_code(full_code, new_string, merged)
    return {
        "violations": violations,
        "passed": len(violations) == 0,
    }
