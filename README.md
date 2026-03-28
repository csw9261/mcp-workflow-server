# mcp-workflow-server

Claude Code에 자연어로 요청하면 FastAPI 서버가 자동으로 Global/Team/Project Rules를 감지하여 요청에 반영하고, 생성된 결과물을 규칙 기반으로 검증하는 시스템.

---

## 구현 상태

- [x] FastAPI 서버 (`/get_rules`, `/health`)
- [x] Hook 1 (UserPromptSubmit) - rules 자동 주입
- [x] Hook 2 (PostToolUse) - Claude 자체 검증 요청 (별도 API 키 불필요)
- [x] Rule Engine - global/team/project 계층 병합 및 우선순위
- [x] rules-repo - 디렉토리 전체 스캔 (yaml 파일 여러 개 분리 가능)
- [x] Ralph 파이프라인 - `claude -p` 반복 실행 + Stop Hook 완료 판단
- [x] WORKFLOW_MODE - interactive / ralph / off 모드 지원

> 서버는 ngrok으로 외부 접속 가능. `WORKFLOW_SERVER_URL` 환경변수로 서버 주소 변경.

---

## 아키텍처

```
개발자가 Claude Code에 프롬프트 입력
              │
              ▼
┌─────────────────────────────────────┐
│ Hook 1 - UserPromptSubmit           │
│ inject_rules_hook.py                │
│   .workflow.yaml 탐색 (상위 탐색)   │
│   POST /get_rules {team, project}   │
│       ↓                             │
│   FastAPI Server                    │
│   global/team/project rules 로드    │
│       ↓                             │
│   plain text stdout → 컨텍스트 주입 │
└─────────────────────────────────────┘
              │
              ▼
    Claude가 rules를 인지한 상태로 요청 처리
    위반 요청은 이 단계에서 사전 거부
              │
              ▼
    Claude가 코드 작성 (Edit/Write/MultiEdit)
              │
              ▼
┌─────────────────────────────────────┐
│ Hook 2 - PostToolUse                │
│ validate_hook.py                    │
│   .workflow.yaml 탐색 (상위 탐색)   │
│   POST /get_rules {team, project}   │
│       ↓                             │
│   FastAPI Server                    │
│   rules 존재 확인                   │
│       ↓                             │
│   additionalContext JSON →          │
│   "방금 코드 rules 검토해줘" 주입   │
└─────────────────────────────────────┘
              │
              ▼
    Claude가 방금 작성한 코드 재검토
    위반 발견 시 즉시 수정 (이중 안전망)
```

팀원들은 각자 `~/.claude/settings.json`에 hook만 등록하면 됨. 서버 URL은 `WORKFLOW_SERVER_URL` 환경변수로 변경 가능.

---

## 프로젝트 구조

```
mcp-workflow-server/
├── server/                      # 서버 코드 (공용 서버에 배포)
│   ├── api_server.py            # FastAPI 서버 (/get_rules, /health)
│   ├── config.py                # 환경변수 로드 (RULES_REPO_PATH)
│   ├── rule_engine/             # 핵심 로직
│   │   ├── loader.py            # yaml 로드 + 캐싱 (디렉토리 전체 스캔)
│   │   └── merger.py            # global → team → project 우선순위 병합
│   └── rules-repo/              # 실제 rules 파일들
│       ├── global/
│       │   ├── security.yaml
│       │   └── code-style.yaml
│       ├── teams/
│       │   └── dev-team-1/
│       │       └── rules.yaml
│       └── projects/
│           └── sample-project/
│               └── rules.yaml
│
├── client/                      # 팀원 로컬에 설치하는 코드
│   └── hooks/
│       ├── inject_rules_hook.py # Hook 1 - UserPromptSubmit
│       └── validate_hook.py     # Hook 2 - PostToolUse
│
├── requirements.txt
└── .workflow.yaml               # 이 레포 자체의 team/project 설정 (테스트용)
```

호출 흐름:
```
client/hooks/ → server/api_server.py → server/rule_engine/ → server/rules-repo/
```

---

## 서버 설치 (관리자)

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

### 3. FastAPI 서버 기동

```bash
# 포그라운드
.venv/bin/python server/api_server.py

# 백그라운드
nohup .venv/bin/python server/api_server.py > /tmp/workflow-server.log 2>&1 &

# 포트 변경 시
PORT=27842 .venv/bin/python server/api_server.py
```

동작 확인:
```bash
curl http://localhost:27842/health
# {"status":"ok"}
```

---

## 팀원 온보딩 (클라이언트)

서버가 이미 떠 있는 상태에서 팀원이 연결하는 방법.

### 1. 레포 클론 또는 client/hooks/ 파일 복사

```bash
git clone https://github.com/your-org/mcp-workflow-server.git
```

또는 `client/hooks/inject_rules_hook.py`, `client/hooks/validate_hook.py` 두 파일만 복사.

> hook 파일은 표준 라이브러리만 사용하므로 별도 패키지 설치 불필요.

### 2. ~/.claude/settings.json 등록

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "/path/to/python /path/to/client/hooks/inject_rules_hook.py"
      }]
    }],
    "PostToolUse": [{
      "matcher": "Edit|Write|MultiEdit",
      "hooks": [{
        "type": "command",
        "command": "/path/to/python /path/to/client/hooks/validate_hook.py"
      }]
    }]
  },
  "env": {
    "WORKFLOW_SERVER_URL": "http://team-server:27842"
  }
}
```

> `/path/to/python`은 본인 환경의 python 경로로 변경. `WORKFLOW_SERVER_URL`은 서버 주소로 변경.

### 3. 프로젝트 루트에 .workflow.yaml 추가

작업할 프로젝트 루트에 `.workflow.yaml` 파일 생성:

```yaml
team: dev-team-1
project: my-project
```

팀명/프로젝트명은 서버의 `rules-repo/teams/`, `rules-repo/projects/` 디렉토리명과 일치해야 함.

### 4. 동작 확인

Claude Code 재시작 후 아무 프롬프트나 입력하면 rules가 주입된 것 확인 가능:

```
[WORKFLOW RULES - 적용: project=my-project, team=dev-team-1, global]
- [sec-001] ...
...
[/WORKFLOW RULES]
```
```

### 5. Hook 비활성화 (원상복구)


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

클라이언트(hook)에서 감지 후 서버에 전송:

1. cwd에서 상위 디렉토리까지 `.workflow.yaml` 탐색 ← team rules 적용하려면 필수
2. fallback → global rules만 적용

`.workflow.yaml` 예시:
```yaml
team: dev-team-1
project: sample-project
```

---

## 동작 방식

### Hook 1 - UserPromptSubmit (rules 주입)

1. 프롬프트 전송 시 자동 발동
2. Hook 스크립트가 cwd에서 상위 디렉토리까지 `.workflow.yaml` 탐색 → team/project 추출
3. `POST /get_rules {team, project}` 요청을 서버에 전송
4. 서버가 rules 로드 & 병합 → plain text 반환
5. Hook 스크립트가 반환된 rules를 stdout 출력 → Claude 컨텍스트에 자동 주입
6. Claude가 rules를 인지한 상태에서 요청을 처리 → 위반 요청은 사전에 거부
- **주의**: `additionalContext` JSON 포맷은 동작 안 함. plain text만 동작.

### Hook 2 - PostToolUse (이중 검증)

1. Edit/Write/MultiEdit 완료 후 발동
2. Hook 스크립트가 cwd에서 상위 디렉토리까지 `.workflow.yaml` 탐색 → team/project 추출
3. `POST /get_rules {team, project}` 전송하여 rules가 있는지 확인
3. `hookSpecificOutput.additionalContext` JSON으로 Claude에게 검증 요청 주입
4. **Claude가 방금 작성한 코드를 rules 기준으로 재검토 & 위반 시 즉시 수정** (이중 안전망)
   - Hook 1에서 걸러지지 않은 위반을 사후에 한번 더 잡아냄
   - 별도 API 호출 없음, ANTHROPIC_API_KEY 불필요
- **주의**: `hookSpecificOutput.additionalContext` JSON 포맷만 동작. plain text는 동작 안 함.

### API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|---|---|---|
| `/health` | GET | 서버 상태 확인 |
| `/get_rules` | POST | team/project 기반 rules 반환 |

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

