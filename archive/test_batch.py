#!/usr/bin/env python3
"""배치 API 테스트 스크립트"""
from datetime import date, timedelta
from app.services.data_collector import ETFDataCollector

# Collector 생성
collector = ETFDataCollector()

# 날짜 계산
end_date = date.today()
start_date = end_date - timedelta(days=5)

print(f"테스트 기간: {start_date} ~ {end_date}")

# 가격 데이터 조회
ticker = "487240"
print(f"\n[{ticker}] 가격 데이터 조회 중...")
prices = collector.get_price_data(ticker, start_date, end_date)
print(f"조회된 가격 데이터: {len(prices)}건")

if prices:
    print(f"\n최신 가격 데이터:")
    p = prices[0]
    print(f"  날짜: {p.date}")
    print(f"  종가: {p.close_price}")
    print(f"  거래량: {p.volume}")

# 매매동향 조회
print(f"\n[{ticker}] 매매동향 조회 중...")
trading_flow = collector.get_trading_flow_data(ticker, start_date, end_date)
print(f"조회된 매매동향 데이터: {len(trading_flow)}건")

if trading_flow:
    print(f"\n최신 매매동향:")
    t = trading_flow[0]
    print(f"  날짜: {t.date}")
    print(f"  개인: {t.individual_net}")
    print(f"  기관: {t.institutional_net}")
    print(f"  외국인: {t.foreign_net}")
