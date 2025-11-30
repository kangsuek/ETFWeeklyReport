#!/usr/bin/env python3
"""
데이터 백필 스크립트
과거 데이터를 수집합니다.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scheduler import DataCollectionScheduler

def main():
    """30일치 데이터 백필"""
    print("=" * 50)
    print("데이터 백필 시작 (30일)")
    print("=" * 50)

    scheduler = DataCollectionScheduler()
    scheduler.backfill_historical_data(days=30)

    print("=" * 50)
    print("데이터 백필 완료")
    print("=" * 50)

if __name__ == "__main__":
    main()
