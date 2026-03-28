def merge_rules(raw_rules: dict) -> list:
    """
    global → team → project 순서로 병합.
    같은 id 충돌 시 더 구체적인(하위) 규칙이 우선 적용.
    """
    # id를 키로 쓰는 dict에 순서대로 덮어써서 우선순위를 구현
    # 나중에 쓰인 값(더 구체적인 레이어)이 이전 값을 덮어씀
    merged: dict[str, dict] = {}

    for layer in ["global", "team", "project"]:
        for rule in raw_rules.get(layer, []):
            merged[rule["id"]] = rule  # 동일 id면 더 구체적인 레이어의 rule로 교체

    # dict 삽입 순서(Python 3.7+)가 유지되므로 global 순서 기반으로 반환됨
    return list(merged.values())
