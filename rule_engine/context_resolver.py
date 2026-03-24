import os
import yaml
import subprocess


def resolve_context(cwd: str) -> dict:
    """
    cwd 기반으로 team/project 컨텍스트를 자동 감지.

    1순위: .workflow.yaml
    2순위: git remote URL에서 project 추출
    3순위: fallback → global only
    """
    context = {"team": None, "project": None, "warnings": []}

    # 1순위: .workflow.yaml
    workflow_path = os.path.join(cwd, ".workflow.yaml")
    if os.path.exists(workflow_path):
        with open(workflow_path) as f:
            config = yaml.safe_load(f) or {}
        context["team"] = config.get("team")
        context["project"] = config.get("project")
        return context

    # 2순위: git remote URL에서 project 추출
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            remote_url = result.stdout.strip()
            project = remote_url.rstrip("/").split("/")[-1].removesuffix(".git")
            context["project"] = project
            context["warnings"].append("⚠ .workflow.yaml 추가를 권장합니다 (team rules 미적용)")
            return context
    except Exception:
        pass

    # 3순위: fallback
    context["warnings"].append("⚠ .workflow.yaml 없음 → global rules만 적용")
    return context
