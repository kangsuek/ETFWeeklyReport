"""
공유 pytest 픽스처 및 마커 설정
"""
import pytest


def pytest_configure(config):
    """커스텀 마커 등록"""
    config.addinivalue_line(
        "markers",
        "postgres: PostgreSQL 전용 테스트. 실행 전 'just pg-up' 필요."
    )
