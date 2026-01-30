#!/usr/bin/env python3
"""
분봉 데이터 조회 확인 스크립트

오늘 날짜의 분봉 데이터가 09:00~15:30 범위에서 조회되는지 확인합니다.

사용 (backend/ 에서, 가상환경 활성화 후):
  python3 scripts/check_intraday_data.py 487240
  python3 scripts/check_intraday_data.py 487240 --date 2026-01-29
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import date, datetime
from app.services.intraday_collector import IntradayDataCollector
from app.database import get_db_connection, get_cursor, USE_POSTGRES

def check_intraday_data(ticker: str, target_date: date = None):
    """분봉 데이터 조회 범위 확인"""
    if target_date is None:
        target_date = date.today()
    
    collector = IntradayDataCollector()
    
    print(f"\n{'='*60}")
    print(f"분봉 데이터 조회 확인")
    print(f"{'='*60}")
    print(f"종목 코드: {ticker}")
    print(f"조회 날짜: {target_date}")
    print(f"예상 범위: 09:00 ~ 15:30")
    print(f"{'='*60}\n")
    
    # 1. get_intraday_data로 조회 (09:00~15:30 필터링)
    print("1. API 조회 방식 (09:00~15:30 필터링)")
    print("-" * 60)
    intraday_data = collector.get_intraday_data(ticker, target_date)
    
    if not intraday_data:
        print("❌ 데이터 없음")
        print("\n2. DB에 저장된 전체 데이터 확인")
        print("-" * 60)
        
        # DB에서 해당 날짜의 모든 데이터 확인
        p = "%s" if USE_POSTGRES else "?"
        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)
            
            # 해당 날짜의 모든 분봉 데이터 조회 (필터링 없이)
            start_of_day = datetime.combine(target_date, datetime.min.time())
            end_of_day = datetime.combine(target_date, datetime.max.time())
            
            query = f"""
                SELECT datetime, price, volume
                FROM intraday_prices
                WHERE ticker = {p} 
                AND datetime >= {p} 
                AND datetime < {p}
                ORDER BY datetime ASC
            """
            cursor.execute(query, (ticker, start_of_day, end_of_day))
            all_rows = cursor.fetchall()
            
            if all_rows:
                print(f"✅ DB에 저장된 데이터: {len(all_rows)}건")
                first_dt = all_rows[0]['datetime']
                last_dt = all_rows[-1]['datetime']
                
                if isinstance(first_dt, str):
                    first_dt = datetime.fromisoformat(first_dt.replace(' ', 'T'))
                    last_dt = datetime.fromisoformat(last_dt.replace(' ', 'T'))
                
                print(f"   첫 데이터: {first_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   마지막 데이터: {last_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 09:00 이전 데이터가 있는지 확인
                market_start = datetime.combine(target_date, datetime.min.time().replace(hour=9, minute=0))
                if first_dt > market_start:
                    print(f"\n⚠️  경고: 첫 데이터가 09:00 이후입니다!")
                    print(f"   장 시작(09:00) 데이터가 누락되었을 수 있습니다.")
            else:
                print("❌ DB에 해당 날짜 데이터 없음")
    else:
        print(f"✅ 조회된 데이터: {len(intraday_data)}건")
        
        # 첫 번째와 마지막 데이터 시간 확인
        first_item = intraday_data[0]
        last_item = intraday_data[-1]
        
        first_dt = first_item['datetime']
        last_dt = last_item['datetime']
        
        if isinstance(first_dt, str):
            first_dt = datetime.fromisoformat(first_dt.replace(' ', 'T'))
            last_dt = datetime.fromisoformat(last_dt.replace(' ', 'T'))
        
        first_time = first_dt.strftime('%H:%M')
        last_time = last_dt.strftime('%H:%M')
        
        print(f"   첫 데이터 시간: {first_time}")
        print(f"   마지막 데이터 시간: {last_time}")
        
        # 09:00~15:30 범위 확인
        expected_start = "09:00"
        expected_end = "15:30"
        
        if first_time == expected_start:
            print(f"   ✅ 장 시작 시간(09:00) 데이터 포함")
        else:
            print(f"   ⚠️  장 시작 시간(09:00) 데이터 누락 (첫 데이터: {first_time})")
        
        if last_time == expected_end or last_time <= expected_end:
            print(f"   ✅ 장 종료 시간(15:30) 이하 데이터 포함")
        else:
            print(f"   ⚠️  장 종료 시간(15:30) 초과 데이터 포함 (마지막 데이터: {last_time})")
        
        # 시간대별 데이터 분포 확인
        print(f"\n2. 시간대별 데이터 분포")
        print("-" * 60)
        time_distribution = {}
        for item in intraday_data:
            dt = item['datetime']
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace(' ', 'T'))
            hour = dt.hour
            if hour not in time_distribution:
                time_distribution[hour] = 0
            time_distribution[hour] += 1
        
        for hour in sorted(time_distribution.keys()):
            count = time_distribution[hour]
            bar = "█" * (count // 10)  # 간단한 시각화
            print(f"   {hour:02d}시: {count:3d}건 {bar}")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    import argparse

    # 사용: python3 scripts/check_intraday_data.py 487240
    #      python3 scripts/check_intraday_data.py 487240 --date 2026-01-29
    parser = argparse.ArgumentParser(description="분봉 데이터 조회 확인")
    parser.add_argument("ticker", help="종목 코드")
    parser.add_argument("--date", help="조회할 날짜 (YYYY-MM-DD, 기본: 오늘)", default=None)

    args = parser.parse_args()

    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()

    check_intraday_data(args.ticker, target_date)
