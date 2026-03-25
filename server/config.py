import os
from dotenv import load_dotenv

load_dotenv()

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_REPO_PATH = os.getenv("RULES_REPO_PATH", os.path.join(_BASE_DIR, "rules-repo"))
