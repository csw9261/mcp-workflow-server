import os
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

# 이 파일(config.py)이 위치한 디렉토리의 절대 경로
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 워크플로우 룰 저장소 경로. 환경변수 RULES_REPO_PATH가 없으면 server/rules-repo를 기본값으로 사용
RULES_REPO_PATH = os.getenv("RULES_REPO_PATH", os.path.join(_BASE_DIR, "rules-repo"))
