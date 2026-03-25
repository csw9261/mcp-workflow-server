def merge_rules(raw_rules: dict) -> list:
    """
    global → team → project 순서로 병합.
    같은 id 충돌 시 더 구체적인(하위) 규칙이 우선 적용.
    """
    merged: dict[str, dict] = {}

    for layer in ["global", "team", "project"]:
        for rule in raw_rules.get(layer, []):
            merged[rule["id"]] = rule

    return list(merged.values())
