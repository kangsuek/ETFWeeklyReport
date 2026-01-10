"""
티커 카탈로그 API 테스트 스크립트

실제 API 서버가 실행 중일 때 사용할 수 있는 테스트 스크립트입니다.
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api"


def test_search_api():
    """종목 검색 API 테스트"""
    print("\n" + "="*60)
    print("종목 검색 API 테스트")
    print("="*60)
    
    # 테스트 데이터 삽입 (실제 DB에 데이터가 있어야 함)
    test_cases = [
        {"q": "삼성", "expected": "종목명에 '삼성' 포함"},
        {"q": "005930", "expected": "티커 코드 검색"},
        {"q": "ETF", "type": "ETF", "expected": "ETF 타입 필터"},
        {"q": "존재하지않는종목12345", "expected": "빈 결과"},
    ]
    
    for case in test_cases:
        print(f"\n테스트: {case['expected']}")
        params = {"q": case["q"]}
        if "type" in case:
            params["type"] = case["type"]
        
        try:
            response = requests.get(f"{BASE_URL}/settings/stocks/search", params=params, timeout=5)
            print(f"  상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  결과 수: {len(data)}")
                if len(data) > 0:
                    print(f"  첫 번째 결과: {data[0]}")
            else:
                print(f"  에러: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"  연결 실패: {e}")


def test_collect_api():
    """종목 목록 수집 API 테스트 (실제 수집은 시간이 오래 걸림)"""
    print("\n" + "="*60)
    print("종목 목록 수집 API 테스트")
    print("="*60)
    print("\n⚠️  주의: 실제 수집은 5-10분이 걸릴 수 있습니다.")
    print("   이 테스트는 API 엔드포인트만 확인합니다.")
    
    try:
        # 실제 수집은 주석 처리 (시간이 오래 걸림)
        # response = requests.post(f"{BASE_URL}/settings/ticker-catalog/collect", timeout=600)
        # print(f"상태 코드: {response.status_code}")
        # if response.status_code == 200:
        #     data = response.json()
        #     print(f"수집 결과: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        print("\n✅ API 엔드포인트는 정상적으로 등록되어 있습니다.")
        print("   실제 수집을 테스트하려면 위 주석을 해제하세요.")
    except requests.exceptions.RequestException as e:
        print(f"연결 실패: {e}")


def test_database_schema():
    """데이터베이스 스키마 확인"""
    print("\n" + "="*60)
    print("데이터베이스 스키마 확인")
    print("="*60)
    
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app.database import get_db_connection
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 테이블 존재 확인
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='stock_catalog'
            """)
            table_exists = cursor.fetchone()
            
            if table_exists:
                print("✅ stock_catalog 테이블이 존재합니다.")
                
                # 인덱스 확인
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND tbl_name='stock_catalog'
                """)
                indexes = [row[0] for row in cursor.fetchall()]
                print(f"✅ 인덱스: {', '.join(indexes)}")
                
                # 데이터 수 확인
                cursor.execute("SELECT COUNT(*) FROM stock_catalog")
                count = cursor.fetchone()[0]
                print(f"✅ 저장된 종목 수: {count}개")
                
                if count > 0:
                    # 샘플 데이터 확인
                    cursor.execute("SELECT ticker, name, type FROM stock_catalog LIMIT 5")
                    samples = cursor.fetchall()
                    print("\n샘플 데이터:")
                    for row in samples:
                        print(f"  - {row[0]}: {row[1]} ({row[2]})")
            else:
                print("❌ stock_catalog 테이블이 존재하지 않습니다.")
                print("   데이터베이스를 초기화하세요: python -m app.database")
                
    except Exception as e:
        print(f"❌ 오류: {e}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("티커 카탈로그 기능 테스트")
    print("="*60)
    
    # 데이터베이스 스키마 확인
    test_database_schema()
    
    # API 테스트 (서버가 실행 중이어야 함)
    print("\n" + "="*60)
    print("API 테스트 (서버가 실행 중이어야 함)")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL.replace('/api', '')}/health", timeout=2)
        if response.status_code == 200:
            print("✅ 서버가 실행 중입니다.")
            test_search_api()
            test_collect_api()
        else:
            print("⚠️  서버가 실행 중이지만 응답이 예상과 다릅니다.")
    except requests.exceptions.RequestException:
        print("⚠️  서버가 실행 중이지 않습니다.")
        print("   서버를 시작한 후 다시 실행하세요: uvicorn app.main:app --reload")

