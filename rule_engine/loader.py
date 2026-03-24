import os
import yaml
from config import RULES_REPO_PATH

_cache: dict = {}


def load_rules(context: dict) -> dict:
    """global / team / project rules를 로드하여 반환"""
    rules_repo = os.path.abspath(RULES_REPO_PATH)

    result = {
        "global": _load_dir(os.path.join(rules_repo, "global")),
        "team": [],
        "project": [],
    }

    if context.get("team"):
        team_dir = os.path.join(rules_repo, "teams", context["team"])
        result["team"] = _load_dir(team_dir)

    if context.get("project"):
        project_dir = os.path.join(rules_repo, "projects", context["project"])
        result["project"] = _load_dir(project_dir)

    return result


def _load_dir(path: str) -> list:
    rules = []
    if not os.path.isdir(path):
        return rules
    for filename in sorted(os.listdir(path)):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            rules.extend(_load_file(os.path.join(path, filename)))
    return rules


def _load_file(path: str) -> list:
    if path in _cache:
        return _cache[path]
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    rules = data.get("rules", [])
    # source 필드 주입
    for rule in rules:
        if "source" not in rule:
            rule["source"] = os.path.relpath(path, RULES_REPO_PATH)
    _cache[path] = rules
    return rules
