import json
import anthropic
from config import ANTHROPIC_API_KEY


def validate_code(full_code: str, new_string: str | None, rules: list) -> list:
    """
    변경된 코드(new_string)를 전체 파일(full_code) 컨텍스트와 함께 Claude API로 검증.
    new_string이 None이면 full_code 전체를 검증 (Ralph Stop Hook용).
    """
    if not rules:
        return []

    rules_text = "\n".join(
        f"- [{r['id']}] {r['description']} (severity: {r.get('severity', 'error')}, 출처: {r.get('source', 'unknown')})"
        for r in rules
    )

    if new_string:
        target_section = f"""
전체 파일 (컨텍스트용):
```
{full_code}
```

방금 변경된 부분 (검증 대상):
```
{new_string}
```
"""
        instruction = "**변경된 부분만** 아래 rules를 기준으로 위반 여부를 판단해주세요."
    else:
        target_section = f"""
전체 파일 (검증 대상):
```
{full_code}
```
"""
        instruction = "아래 rules를 기준으로 위반 여부를 판단해주세요."

    prompt = f"""{target_section}

Rules:
{rules_text}

{instruction}

JSON 형식으로만 응답해주세요 (다른 텍스트 없이):
{{
  "violations": [
    {{"id": "rule-id", "description": "위반 내용 설명", "line": 0, "source": "출처"}}
  ]
}}

위반이 없으면 violations를 빈 배열로 반환하세요."""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # JSON 블록 추출
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    data = json.loads(text)
    return data.get("violations", [])
