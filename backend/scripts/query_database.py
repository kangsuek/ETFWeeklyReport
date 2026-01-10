#!/usr/bin/env python3
"""
SQLite 데이터베이스 조회 스크립트
"""
import sqlite3
import sys
from pathlib import Path

# 데이터베이스 경로
DB_PATH = Path(__file__).parent.parent / "data" / "etf_data.db"


def print_header(title):
    """헤더 출력"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def get_all_etfs():
    """전체 종목 목록 조회"""
    print_header("1️⃣  전체 종목 목록")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ticker, name, type, theme, expense_ratio
        FROM etfs
        ORDER BY type, ticker
    """)
    
    print(f"\n{'종목코드':<10} {'종목명':<30} {'타입':<8} {'테마':<12} {'보수율':<8}")
    print("-" * 80)
    
    for row in cursor.fetchall():
        ticker, name, type_, theme, expense_ratio = row
        expense = f"{expense_ratio:.2%}" if expense_ratio else "N/A"
        print(f"{ticker:<10} {name:<30} {type_:<8} {theme:<12} {expense:<8}")
    
    conn.close()


def get_data_statistics():
    """수집된 데이터 통계"""
    print_header("2️⃣  수집된 데이터 통계")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            e.ticker,
            e.name,
            COUNT(p.id) as record_count,
            MIN(p.date) as first_date,
            MAX(p.date) as last_date
        FROM etfs e
        LEFT JOIN prices p ON e.ticker = p.ticker
        GROUP BY e.ticker, e.name
        ORDER BY record_count DESC
    """)
    
    print(f"\n{'종목코드':<10} {'종목명':<25} {'레코드수':<10} {'최초날짜':<12} {'최근날짜':<12}")
    print("-" * 80)
    
    for row in cursor.fetchall():
        ticker, name, count, first_date, last_date = row
        first = first_date if first_date else "-"
        last = last_date if last_date else "-"
        print(f"{ticker:<10} {name:<25} {count:<10} {first:<12} {last:<12}")
    
    conn.close()


def get_price_details(ticker):
    """특정 종목의 가격 데이터 상세 조회"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 종목 정보
    cursor.execute("SELECT name, type FROM etfs WHERE ticker = ?", (ticker,))
    result = cursor.fetchone()
    
    if not result:
        print(f"\n❌ 종목 {ticker}을(를) 찾을 수 없습니다.")
        conn.close()
        return
    
    name, type_ = result
    print_header(f"3️⃣  {name} ({ticker}) 가격 데이터")
    
    # 가격 데이터
    cursor.execute("""
        SELECT 
            date,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            daily_change_pct
        FROM prices
        WHERE ticker = ?
        ORDER BY date DESC
        LIMIT 10
    """, (ticker,))
    
    rows = cursor.fetchall()
    
    if not rows:
        print(f"\n⚠️  수집된 데이터가 없습니다.")
        conn.close()
        return
    
    print(f"\n최근 {len(rows)}일 데이터:")
    print(f"\n{'날짜':<12} {'시가':<12} {'고가':<12} {'저가':<12} {'종가':<12} {'거래량':<12} {'등락률':<8}")
    print("-" * 90)
    
    for row in rows:
        date, open_p, high_p, low_p, close_p, volume, change = row
        open_str = f"{open_p:,.0f}" if open_p else "-"
        high_str = f"{high_p:,.0f}" if high_p else "-"
        low_str = f"{low_p:,.0f}" if low_p else "-"
        close_str = f"{close_p:,.0f}" if close_p else "-"
        volume_str = f"{volume:,.0f}" if volume else "-"
        change_str = f"{change:+.2f}%" if change is not None else "-"
        
        print(f"{date:<12} {open_str:<12} {high_str:<12} {low_str:<12} {close_str:<12} {volume_str:<12} {change_str:<8}")
    
    # 통계 정보
    cursor.execute("""
        SELECT 
            COUNT(*) as total_records,
            AVG(close_price) as avg_price,
            MAX(close_price) as max_price,
            MIN(close_price) as min_price,
            SUM(volume) as total_volume
        FROM prices
        WHERE ticker = ?
    """, (ticker,))
    
    stats = cursor.fetchone()
    total, avg_price, max_price, min_price, total_volume = stats
    
    print(f"\n📊 통계:")
    print(f"   총 레코드: {total}개")
    print(f"   평균 종가: {avg_price:,.0f}원")
    print(f"   최고가: {max_price:,.0f}원")
    print(f"   최저가: {min_price:,.0f}원")
    print(f"   총 거래량: {total_volume:,.0f}주")
    
    conn.close()


def get_all_stocks_summary():
    """전체 종목 요약"""
    print_header("4️⃣  전체 종목 최근 데이터 요약")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            e.ticker,
            e.name,
            e.type,
            (SELECT close_price FROM prices WHERE ticker = e.ticker ORDER BY date DESC LIMIT 1) as latest_price,
            (SELECT date FROM prices WHERE ticker = e.ticker ORDER BY date DESC LIMIT 1) as latest_date,
            (SELECT daily_change_pct FROM prices WHERE ticker = e.ticker ORDER BY date DESC LIMIT 1) as latest_change
        FROM etfs e
        ORDER BY e.type, e.ticker
    """)
    
    print(f"\n{'종목코드':<10} {'종목명':<28} {'타입':<8} {'최근가':<12} {'날짜':<12} {'등락률':<8}")
    print("-" * 85)
    
    for row in cursor.fetchall():
        ticker, name, type_, price, date, change = row
        price_str = f"{price:,.0f}원" if price else "-"
        date_str = date if date else "-"
        change_str = f"{change:+.2f}%" if change is not None else "-"
        
        print(f"{ticker:<10} {name:<28} {type_:<8} {price_str:<12} {date_str:<12} {change_str:<8}")
    
    conn.close()


def interactive_query():
    """대화형 조회"""
    print("\n" + "=" * 60)
    print("  SQLite 데이터베이스 대화형 조회")
    print("=" * 60)
    print("\n명령어:")
    print("  1 - 전체 종목 목록")
    print("  2 - 수집 데이터 통계")
    print("  3 - 특정 종목 상세 (종목코드 입력)")
    print("  4 - 전체 종목 요약")
    print("  q - 종료")
    print("-" * 60)
    
    while True:
        try:
            command = input("\n명령어 입력 > ").strip()
            
            if command == 'q':
                print("\n종료합니다.")
                break
            elif command == '1':
                get_all_etfs()
            elif command == '2':
                get_data_statistics()
            elif command == '3':
                ticker = input("종목코드 입력 (예: 487240) > ").strip()
                if ticker:
                    get_price_details(ticker)
            elif command == '4':
                get_all_stocks_summary()
            else:
                print("❌ 잘못된 명령어입니다.")
        except KeyboardInterrupt:
            print("\n\n종료합니다.")
            break
        except Exception as e:
            print(f"❌ 오류: {e}")


def main():
    """메인 함수"""
    if not DB_PATH.exists():
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {DB_PATH}")
        sys.exit(1)
    
    # 인자가 있으면 특정 종목 조회
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        get_price_details(ticker)
    else:
        # 전체 정보 출력
        get_all_etfs()
        get_data_statistics()
        get_all_stocks_summary()
        
        # 대화형 모드 시작 여부 물어보기
        print("\n대화형 모드로 전환하시겠습니까? (y/n) ", end="")
        if input().strip().lower() == 'y':
            interactive_query()


if __name__ == "__main__":
    main()

