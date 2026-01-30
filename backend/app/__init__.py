"""
ETF Weekly Report Backend Application

Load environment variables from project root .env
"""
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트의 .env 로드 (backend/app/__init__.py -> 루트는 parent.parent.parent)
_root_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_root_dir / ".env")
