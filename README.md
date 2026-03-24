# mcp-workflow-server

Claude Code에 자연어로 요청하면 FastAPI 서버가 자동으로 Global/Team/Project Rules를 감지하여 요청에 반영하고, 생성된 결과물을 규칙 기반으로 검증하는 시스템.

---

## 구현 상태

### 완료
- [x] Hook 1 (UserPromptSubmit) - rules 자동 주입 동작 확인
- [x] Rule Engine - context_resolver, loader, merger 동작 확인
- [x] global / team / project 계층 병합 및 우선순위 동작 확인
- [x] rules-repo 샘플 구조 (global/team/project 전부 디렉토리 전체 스캔)
- [x] FastAPI 서버 - Hook이 로컬 import 대신 HTTP 요청으로 rules 수신

### 미완료
- [ ] Hook 2 (PostToolUse) - validate_code() → ANTHROPIC_API_KEY 필요
- [ ] Ralph 모드 Stop Hook (2단계)
- [ ] Remote 배포 (현재는 localhost:8000 기준)

---

## 아키텍처

```
[Claude Code]
    │
    ├── UserPromptSubmit Hook
    │       │  POST /get_rules {cwd}
    │       ▼
    │   [FastAPI Server]  ←── rules-repo/ (yaml 파일들)
    │       │
    │       │  rules plain text 반환
    │       ▼
    │   Claude 컨텍스트에 자동 주입
    │
    └── PostToolUse Hook (Edit/Write/MultiEdit)
            │  POST /validate_code {cwd, file_path, new_string, full_code}
            ▼
        [FastAPI Server] → Claude API로 위반 검증
            │
            └── 위반 시 경고 출력
```

팀원들은 각자 `~/.claude/settings.json`에 hook만 등록하면 됨. 서버 URL은 `WORKFLOW_SERVER_URL` 환경변수로 변경 가능.

---

## 프로젝트 구조

```
mcp-workflow-server/
├── api_server.py                # FastAPI 서버 (/get_rules, /validate_code, /health)
├── config.py                    # 환경변수 로드
├── requirements.txt
├── .env.example
├── .workflow.yaml               # 현재 프로젝트 team/project 설정 (테스트용)
│
├── rule_engine/
│   ├── context_resolver.py      # .workflow.yaml / git remote로 team/project 감지
│   ├── loader.py                # yaml 로드 + 캐싱 (디렉토리 전체 스캔)
│   ├── merger.py                # global → team → project 우선순위 병합
│   └── validator.py             # Claude API로 코드 위반 검증
│
├── hooks/
│   ├── inject_rules_hook.py     # Hook 1 - UserPromptSubmit (서버에 HTTP 요청)
│   └── validate_hook.py         # Hook 2 - PostToolUse (서버에 HTTP 요청)
│
└── rules-repo/
    ├── global/
    │   ├── security.yaml
    │   └── code-style.yaml
    ├── teams/
    │   └── dev-team-1/
    │       └── rules.yaml
    └── projects/
        └── sample-project/
            └── rules.yaml
```

---

## 설치 및 설정

### 1. Python 3.10+ 필요

```bash
brew install python@3.13
```

### 2. venv 생성 및 패키지 설치

```bash
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일:
```
ANTHROPIC_API_KEY=your_key_here   # Hook 2 동작에 필요
RULES_REPO_PATH=./rules-repo      # 기본값
```

### 4. FastAPI 서버 기동

```bash
# 포그라운드
.venv/bin/python api_server.py

# 백그라운드
nohup .venv/bin/python api_server.py > /tmp/workflow-server.log 2>&1 &

# 포트 변경 시
PORT=9000 .venv/bin/python api_server.py
```

동작 확인:
```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

> **팀 공유**: 서버를 공용 서버에 배포하고 팀원들 환경변수 `WORKFLOW_SERVER_URL`만 변경하면 됨. Hook 스크립트 자체는 그대로.

### 5. Claude Code settings.json 등록

`~/.claude/settings.json`에 추가 (경로는 본인 환경에 맞게 수정):

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "/path/to/.venv/bin/python /path/to/hooks/inject_rules_hook.py"
      }]
    }],
    "PostToolUse": [{
      "matcher": "Edit|Write|MultiEdit",
      "hooks": [{
        "type": "command",
        "command": "/path/to/.venv/bin/python /path/to/hooks/validate_hook.py"
      }]
    }]
  }
}
```

서버가 기본값(localhost:8000)이 아닌 경우 환경변수 추가:
```json
{
  "env": {
    "WORKFLOW_SERVER_URL": "http://your-server:8000"
  }
}
```

### 6. Hook 비활성화 (원상복구)

hook을 제거하고 싶으면 `~/.claude/settings.json`을 아래 내용으로 교체:

```json
{
  "model": "sonnet"
}
```

---

## Rules 구조

### 계층 우선순위

```
Project Rules  (가장 높음 - 덮어씀)
      ↓
Team Rules
      ↓
Global Rules   (가장 낮음)
```

같은 id 충돌 시 하위(더 구체적인) 규칙이 우선 적용.

### yaml 포맷

```yaml
rules:
  - id: sec-001
    description: "raw SQL query 금지, ORM만 사용"
    severity: error    # error | warning
```

### rules-repo 파일 구조

global/teams/projects 모두 디렉토리 전체 스캔. 파일명 무관하게 `.yaml`/`.yml` 전부 로드됨.

```
rules-repo/
├── global/
│   ├── security.yaml      # 파일명 자유
│   └── code-style.yaml
├── teams/
│   └── dev-team-1/
│       ├── rules.yaml     # 파일명 자유
│       └── style.yaml     # 여러 파일로 분리 가능
└── projects/
    └── sample-project/
        ├── rules.yaml
        └── db.yaml        # 여러 파일로 분리 가능
```

### 팀/프로젝트 자동 감지 순서

1. 프로젝트 루트의 `.workflow.yaml` ← team rules 적용하려면 필수
2. git remote URL에서 project만 추출 (team 감지 불가)
3. fallback → global rules만 적용

`.workflow.yaml` 예시:
```yaml
team: dev-team-1
project: sample-project
```

---

## 동작 방식

### Hook 1 - UserPromptSubmit (rules 주입)

1. 프롬프트 전송 시 자동 발동
2. Hook 스크립트가 `POST /get_rules {cwd}` 요청을 서버에 전송
3. 서버가 cwd 기반으로 `.workflow.yaml` 감지 → rules 로드 & 병합 → plain text 반환
4. Hook 스크립트가 반환된 rules를 stdout 출력 → Claude 컨텍스트에 자동 주입
5. **주의**: `additionalContext` JSON 포맷은 동작 안 함. plain text만 동작.

### Hook 2 - PostToolUse (위반 검증)

1. Edit/Write/MultiEdit 완료 후 발동
2. Hook 스크립트가 `POST /validate_code {cwd, file_path, new_string, full_code}` 전송
3. **서버가 서버 자체의 ANTHROPIC_API_KEY로 Claude API를 별도 호출**하여 위반 검증
   - 사용자의 Claude Code 세션과 독립적인 2차 검증 (심판 역할)
   - 사용자 Claude가 규칙을 무시해도 서버 쪽에서 잡아낼 수 있음
4. 위반 발견 시 경고 출력 (exit 0 - 사용자가 직접 판단)
5. **현재**: 서버에 ANTHROPIC_API_KEY 없으면 동작 안 함 (API 비용 별도 발생)

### API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|---|---|---|
| `/health` | GET | 서버 상태 확인 |
| `/get_rules` | POST | cwd 기반 rules 반환 |
| `/validate_code` | POST | 코드 위반 검증 |

---

## 데모 테스트 질문

아래 질문으로 rules가 실제로 반영되는지 확인할 수 있음.

| 질문 | 확인 포인트 |
|---|---|
| "유저 로그인 함수 만들어줘" | bcrypt 해싱(sec-001), JWT 만료(sec-002) |
| "users 테이블에서 이메일로 유저 조회하는 함수 만들어줘" | SQLAlchemy ORM 사용(sec-003) |
| "유저 생성 API 엔드포인트 만들어줘" | 인증 미들웨어(team-001), 표준 응답 포맷(team-004), type hint(style-003) |
| "User DB 모델 만들어줘" | BaseModel 상속(proj-001), Pydantic 스키마(proj-003) |
| "DB에 유저 저장하는 함수 만들어줘" | 트랜잭션(proj-002), try/except 에러 처리(team-003) |
| "설정 파일에 DB 비밀번호 넣어줘" | 환경변수 관리(sec-004) |

---

## 다음 단계

1. **Hook 2 테스트** - ANTHROPIC_API_KEY 발급 후 validate_code() 동작 확인
2. **Remote 배포** - 공용 서버에 배포, 팀원들 WORKFLOW_SERVER_URL 설정
3. **Ralph 모드** - Stop Hook 연동 (2단계)
