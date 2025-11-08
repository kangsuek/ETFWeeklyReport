"""
6개 대상 종목별 뉴스 검색 테스트
Test news search for 6 target stocks/ETFs
"""

import time
from naver_news_api import search_news, clean_html_tags, parse_pubdate


# 대상 종목 정의
TARGET_STOCKS = [
    {
        "name": "삼성 KODEX AI전력핵심설비 ETF",
        "code": "487240",
        "keywords": ["KODEX AI전력핵심설비", "487240", "AI 전력", "데이터센터 전력"],
        "category": "ETF"
    },
    {
        "name": "신한 SOL 조선TOP3플러스 ETF",
        "code": "466920",
        "keywords": ["SOL 조선TOP3", "466920", "조선 ETF"],
        "category": "ETF"
    },
    {
        "name": "KoAct 글로벌양자컴퓨팅액티브 ETF",
        "code": "0020H0",
        "keywords": ["KoAct 양자컴퓨팅", "0020H0", "양자컴퓨팅 ETF"],
        "category": "ETF"
    },
    {
        "name": "KB RISE 글로벌원자력 iSelect ETF",
        "code": "442320",
        "keywords": ["RISE 글로벌원자력", "442320", "원자력 ETF"],
        "category": "ETF"
    },
    {
        "name": "한화오션",
        "code": "042660",
        "keywords": ["한화오션", "042660"],
        "category": "주식"
    },
    {
        "name": "두산에너빌리티",
        "code": "034020",
        "keywords": ["두산에너빌리티", "034020"],
        "category": "주식"
    }
]


def test_single_keyword(keyword: str, display: int = 5):
    """
    단일 키워드로 뉴스 검색 테스트
    """
    try:
        result = search_news(keyword, display=display, sort="date")
        return result
    except Exception as e:
        print(f"   ❌ 에러: {e}")
        return None


def test_all_target_stocks():
    """
    6개 종목 모두 테스트
    """
    print("=" * 80)
    print("6개 대상 종목 뉴스 검색 테스트")
    print("=" * 80)
    print()

    total_results = {}

    for stock in TARGET_STOCKS:
        print(f"{'=' * 80}")
        print(f"[{stock['category']}] {stock['name']} ({stock['code']})")
        print(f"{'=' * 80}")

        # 각 키워드별로 테스트
        best_keyword = None
        best_count = 0

        for keyword in stock['keywords']:
            print(f"\n🔍 키워드: '{keyword}'")

            result = test_single_keyword(keyword, display=5)

            if result:
                total = result['total']
                items_count = len(result['items'])

                print(f"   전체 결과: {total:,}건")
                print(f"   수집된 뉴스: {items_count}건")

                # 가장 많은 결과를 반환한 키워드 저장
                if total > best_count:
                    best_count = total
                    best_keyword = keyword

                # 첫 3개 뉴스 제목만 출력
                if items_count > 0:
                    print(f"   📰 수집된 뉴스:")
                    for i, item in enumerate(result['items'][:3], 1):
                        title_clean = clean_html_tags(item['title'])
                        date_formatted = parse_pubdate(item['pubDate'])
                        print(f"      [{i}] {title_clean[:60]}...")
                        print(f"          날짜: {date_formatted}")
                else:
                    print(f"   ⚠️  검색 결과 없음")

            # API Rate Limiting (0.1초 대기)
            time.sleep(0.1)

        # 최적 키워드 저장
        total_results[stock['code']] = {
            'name': stock['name'],
            'best_keyword': best_keyword,
            'best_count': best_count
        }

        print(f"\n✅ 최적 키워드: '{best_keyword}' ({best_count:,}건)")
        print()

    # 전체 요약
    print("=" * 80)
    print("📊 종목별 최적 검색 키워드 요약")
    print("=" * 80)

    for code, info in total_results.items():
        print(f"{info['name']} ({code})")
        print(f"  → 최적 키워드: '{info['best_keyword']}'")
        print(f"  → 검색 결과: {info['best_count']:,}건")
        print()

    return total_results


if __name__ == "__main__":
    results = test_all_target_stocks()
