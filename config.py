import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
RULES_REPO_PATH = os.getenv("RULES_REPO_PATH", "./rules-repo")
