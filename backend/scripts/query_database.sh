#!/bin/bash
# SQLite 데이터베이스 조회 스크립트

# 스크립트 위치를 기준으로 상대 경로 계산
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB_PATH="$SCRIPT_DIR/../data/etf_data.db"

echo "================================================"
echo "ETF Weekly Report - 데이터베이스 조회"
echo "================================================"
echo ""

# 1. 전체 종목 목록
echo "1️⃣  전체 종목 목록 (6개)"
echo "------------------------------------------------"
sqlite3 -header -column "$DB_PATH" "
SELECT 
    ticker as '종목코드',
    name as '종목명',
    type as '타입',
    theme as '테마'
FROM etfs;
"
echo ""

# 2. 수집된 데이터 통계
echo "2️⃣  수집된 데이터 통계"
echo "------------------------------------------------"
sqlite3 -header -column "$DB_PATH" "
SELECT 
    ticker as '종목코드',
    COUNT(*) as '레코드수'
FROM prices 
GROUP BY ticker 
ORDER BY COUNT(*) DESC;
"
echo ""

# 3. 최근 수집 날짜
echo "3️⃣  종목별 최근 수집 날짜"
echo "------------------------------------------------"
sqlite3 -header -column "$DB_PATH" "
SELECT 
    p.ticker as '종목코드',
    e.name as '종목명',
    MAX(p.date) as '최근날짜',
    COUNT(*) as '총레코드'
FROM prices p
JOIN etfs e ON p.ticker = e.ticker
GROUP BY p.ticker, e.name
ORDER BY MAX(p.date) DESC;
"
echo ""

# 4. 특정 종목 상세 (487240)
echo "4️⃣  KODEX AI전력핵심설비 (487240) 최근 5일 데이터"
echo "------------------------------------------------"
sqlite3 -header -column "$DB_PATH" "
SELECT 
    date as '날짜',
    close_price as '종가',
    volume as '거래량',
    daily_change_pct as '등락률(%)'
FROM prices 
WHERE ticker = '487240'
ORDER BY date DESC 
LIMIT 5;
"
echo ""
echo "================================================"

