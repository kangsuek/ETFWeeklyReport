"""
공유 pytest 픽스처 및 마커 설정
"""
import os
import tempfile
from pathlib import Path

import pytest

# 테스트는 반드시 격리된 임시 DB를 사용한다.
# database.py 가 import 시점에 DATABASE_URL 을 읽어 DB_PATH 를 확정하므로,
# app 모듈이 import 되기 전(=conftest 로드 시점)에 환경변수를 설정해야 한다.
# 이 설정이 없으면 테스트가 실서비스 DB(backend/data/etf_data.db)를 직접 변경해
# 종목목록(stock_catalog) 등 실데이터가 손상된다.
if not os.getenv("DATABASE_URL"):
    _test_db_dir = tempfile.mkdtemp(prefix="etf_test_db_")
    _test_db_path = Path(_test_db_dir) / "test_etf_data.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"


@pytest.fixture(scope="session", autouse=True)
def _init_test_database():
    """세션 시작 시 격리된 테스트 DB 에 스키마를 생성한다."""
    from app.database import DB_PATH, init_db

    # 안전장치: 실서비스 DB 를 대상으로 테스트가 돌지 않도록 방어
    assert "etf_test_db_" in str(DB_PATH), (
        f"테스트가 격리되지 않은 DB 를 사용하려 합니다: {DB_PATH}. "
        "DATABASE_URL 환경변수를 확인하세요."
    )

    init_db()
    yield
