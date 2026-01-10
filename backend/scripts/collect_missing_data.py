"""
누락된 데이터 수집 스크립트

데이터 완전성 점수가 100점이 아닌 종목들의 데이터를 수집합니다.
"""

import sys
from pathlib import Path
import logging

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.data_collector import ETFDataCollector
from app.services.news_scraper import NewsScraper
from app.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """누락된 데이터 수집 메인 함수"""
    print("=" * 80)
    print("누락된 데이터 수집 시작")
    print("=" * 80)

    collector = ETFDataCollector()
    news_scraper = NewsScraper()

    # 수집이 필요한 종목과 필요한 데이터 타입
    tickers_to_collect = {
        '466920': {'price': True, 'trading': True, 'news': False},  # SOL 조선: 가격 추가 + 매매동향
        '034020': {'price': True, 'trading': True, 'news': False},  # 두산에너빌리티: 가격 추가 + 매매동향
        '442320': {'price': True, 'trading': True, 'news': False},  # RISE 원자력: 가격 + 매매동향
        '0020H0': {'price': True, 'trading': True, 'news': True}     # 글로벌양자컴퓨팅: 전체
    }

    stock_config = Config.get_stock_config()

    results = {}

    for ticker, needs in tickers_to_collect.items():
        print(f"\n{'='*80}")
        stock_name = stock_config[ticker]['name']
        print(f"📊 {ticker} ({stock_name}) 데이터 수집 중...")
        print(f"{'='*80}")

        results[ticker] = {
            'name': stock_name,
            'price': None,
            'trading': None,
            'news': None
        }

        # 1. 가격 데이터 수집
        if needs['price']:
            print(f"\n[1/3] 가격 데이터 수집 중 (최근 10일)...")
            try:
                result = collector.collect_and_save_prices(ticker, days=10)
                results[ticker]['price'] = result

                if result['success']:
                    print(f"  ✅ 가격 데이터 수집 완료: {result['records_saved']}건")
                else:
                    print(f"  ⚠️ 가격 데이터 수집 실패: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"  ❌ 가격 데이터 수집 오류: {e}")
                results[ticker]['price'] = {'success': False, 'error': str(e)}
        else:
            print(f"\n[1/3] 가격 데이터: 수집 불필요 (이미 존재)")

        # 2. 매매 동향 수집
        if needs['trading']:
            print(f"\n[2/3] 매매 동향 수집 중 (최근 10일)...")
            try:
                result = collector.collect_and_save_trading_flow(ticker, days=10)
                results[ticker]['trading'] = result

                if result['success']:
                    print(f"  ✅ 매매 동향 수집 완료: {result['records_saved']}건")
                else:
                    print(f"  ⚠️ 매매 동향 수집 실패: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"  ❌ 매매 동향 수집 오류: {e}")
                results[ticker]['trading'] = {'success': False, 'error': str(e)}
        else:
            print(f"\n[2/3] 매매 동향: 수집 불필요 (이미 존재)")

        # 3. 뉴스 수집
        if needs['news']:
            print(f"\n[3/3] 뉴스 수집 중 (최근 7일)...")
            try:
                result = news_scraper.collect_and_save_news(ticker, days=7)
                results[ticker]['news'] = result

                if result['success']:
                    print(f"  ✅ 뉴스 수집 완료: {result['records_saved']}건")
                else:
                    print(f"  ⚠️ 뉴스 수집 실패: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"  ❌ 뉴스 수집 오류: {e}")
                results[ticker]['news'] = {'success': False, 'error': str(e)}
        else:
            print(f"\n[3/3] 뉴스: 수집 불필요 (이미 존재)")

    # 결과 요약
    print(f"\n{'='*80}")
    print("📊 수집 결과 요약")
    print(f"{'='*80}\n")

    for ticker, result in results.items():
        print(f"{ticker} ({result['name']}):")

        if result['price']:
            status = "✅" if result['price'].get('success') else "❌"
            records = result['price'].get('records_saved', 0)
            print(f"  가격: {status} {records}건")

        if result['trading']:
            status = "✅" if result['trading'].get('success') else "❌"
            records = result['trading'].get('records_saved', 0)
            print(f"  매매동향: {status} {records}건")

        if result['news']:
            status = "✅" if result['news'].get('success') else "❌"
            records = result['news'].get('records_saved', 0)
            print(f"  뉴스: {status} {records}건")

        print()

    print("=" * 80)
    print("✅ 데이터 수집 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
