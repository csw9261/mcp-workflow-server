import os
import yaml
from config import RULES_REPO_PATH

# 파일 경로 → rules 리스트 메모리 캐시 (서버 프로세스 재시작 전까지 유지)
_cache: dict = {}


def load_rules(context: dict) -> dict:
    """global / team / project rules를 로드하여 반환"""
    rules_repo = os.path.abspath(RULES_REPO_PATH)

    # global rules는 항상 로드, team/project는 컨텍스트가 있을 때만 로드
    result = {
        "global": _load_dir(os.path.join(rules_repo, "global")),
        "team": [],
        "project": [],
    }

    if context.get("team"):
        # rules-repo/teams/{team}/ 디렉토리에서 로드
        team_dir = os.path.join(rules_repo, "teams", context["team"])
        result["team"] = _load_dir(team_dir)

    if context.get("project"):
        # rules-repo/projects/{project}/ 디렉토리에서 로드
        project_dir = os.path.join(rules_repo, "projects", context["project"])
        result["project"] = _load_dir(project_dir)

    return result


def _load_dir(path: str) -> list:
    """디렉토리 내 모든 .yaml/.yml 파일을 알파벳 순으로 로드"""
    rules = []
    if not os.path.isdir(path):
        return rules  # 디렉토리가 없으면 빈 리스트 반환 (팀/프로젝트 미설정 시 정상 케이스)
    for filename in sorted(os.listdir(path)):  # sorted로 로드 순서를 일관되게 유지
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            rules.extend(_load_file(os.path.join(path, filename)))
    return rules


def _load_file(path: str) -> list:
    """YAML 파일 하나를 파싱하여 rules 리스트 반환. 결과는 캐싱됨."""
    if path in _cache:
        return _cache[path]  # 이미 로드한 파일은 캐시에서 즉시 반환
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    rules = data.get("rules", [])
    # source 필드 주입: 어떤 파일에서 온 rule인지 추적하기 위해 상대 경로를 기록
    for rule in rules:
        if "source" not in rule:
            rule["source"] = os.path.relpath(path, RULES_REPO_PATH)
    _cache[path] = rules
    return rules
