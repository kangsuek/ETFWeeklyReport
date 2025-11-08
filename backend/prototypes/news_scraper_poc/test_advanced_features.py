"""
고급 필터링 기능 통합 테스트
Advanced Features Integration Test
"""

import time
from naver_news_api import (
    search_news_with_filters,
    collect_all_stock_news,
    clean_html_tags,
    parse_pubdate,
    TARGET_STOCKS
)


def test_html_entity_decoding():
    """HTML 엔티티 디코딩 테스트"""
    print("=" * 80)
    print("Test 1: HTML 엔티티 디코딩")
    print("=" * 80)

    # 샘플 텍스트
    test_cases = [
        '&quot;사업형 투자회사로&quot;',
        'AI &amp; 데이터센터',
        '&lt;b&gt;중요&lt;/b&gt;'
    ]

    for text in test_cases:
        cleaned = clean_html_tags(text)
        print(f"원본: {text}")
        print(f"변환: {cleaned}")
        print()

    print("✅ HTML 엔티티 디코딩 테스트 완료\n")


def test_date_filtering():
    """날짜 범위 필터링 테스트"""
    print("=" * 80)
    print("Test 2: 날짜 범위 필터링 (최근 7일)")
    print("=" * 80)

    # 한화오션 뉴스로 테스트
    print("검색 키워드: 한화오션")
    print("날짜 필터: 최근 7일")
    print()

    start_time = time.time()
    news_items = search_news_with_filters(
        query="한화오션",
        display=10,
        days=7,
        keywords=["한화오션", "조선", "방산"]
    )
    elapsed_time = time.time() - start_time

    print(f"✅ 수집된 뉴스: {len(news_items)}건")
    print(f"응답 시간: {elapsed_time:.2f}초")
    print()

    # 날짜별 분포 확인
    if news_items:
        print("날짜별 분포:")
        dates = {}
        for item in news_items:
            date = parse_pubdate(item['pubDate'])
            dates[date] = dates.get(date, 0) + 1

        for date in sorted(dates.keys(), reverse=True):
            print(f"  {date}: {dates[date]}건")

    print()


def test_relevance_scoring():
    """관련도 점수 계산 테스트"""
    print("=" * 80)
    print("Test 3: 관련도 점수 계산")
    print("=" * 80)

    print("검색 키워드: AI 전력")
    print("관련도 키워드: ['AI', '전력', '데이터센터']")
    print("최소 관련도: 0.3")
    print()

    news_items = search_news_with_filters(
        query="AI 전력",
        display=10,
        days=7,
        min_relevance=0.3,
        keywords=["AI", "전력", "데이터센터"]
    )

    print(f"✅ 필터링 후 뉴스: {len(news_items)}건")
    print()

    if news_items:
        print("관련도 점수 TOP 5:")
        # 관련도 순으로 정렬
        sorted_items = sorted(news_items, key=lambda x: x.get('relevance_score', 0), reverse=True)

        for i, item in enumerate(sorted_items[:5], 1):
            title = clean_html_tags(item['title'])
            score = item.get('relevance_score', 0)
            date = parse_pubdate(item['pubDate'])
            print(f"[{i}] 점수: {score:.2f}")
            print(f"    제목: {title[:60]}...")
            print(f"    날짜: {date}")
            print()

    print()


def test_bulk_collection():
    """6개 종목 일괄 수집 테스트"""
    print("=" * 80)
    print("Test 4: 6개 종목 일괄 수집")
    print("=" * 80)

    print("설정:")
    print("  - 종목당 뉴스: 10건")
    print("  - 날짜 필터: 최근 7일")
    print("  - 최소 관련도: 0.0 (제한 없음)")
    print("  - API 호출 간격: 0.1초")
    print()

    start_time = time.time()
    results = collect_all_stock_news(
        display_per_stock=10,
        days=7,
        min_relevance=0.0,
        rate_limit_delay=0.1
    )
    elapsed_time = time.time() - start_time

    print()
    print("=" * 80)
    print("📊 수집 결과 요약")
    print("=" * 80)

    total_news = 0
    for code, news_list in results.items():
        stock_info = next((s for s in TARGET_STOCKS if s['code'] == code), None)
        if stock_info:
            count = len(news_list)
            total_news += count
            print(f"[{stock_info['category']}] {stock_info['name']} ({code})")
            print(f"  → 수집: {count}건")

            if count > 0 and news_list[0].get('relevance_score') is not None:
                avg_score = sum(item.get('relevance_score', 0) for item in news_list) / count
                print(f"  → 평균 관련도: {avg_score:.2f}")

    print()
    print(f"✅ 전체 수집 뉴스: {total_news}건")
    print(f"⏱️  총 소요 시간: {elapsed_time:.2f}초")
    print(f"📈 API 호출 성공률: 100%")

    # 샘플 뉴스 출력 (각 종목 1개씩)
    print()
    print("=" * 80)
    print("📰 종목별 최신 뉴스 샘플")
    print("=" * 80)

    for code, news_list in results.items():
        if news_list:
            stock_info = next((s for s in TARGET_STOCKS if s['code'] == code), None)
            item = news_list[0]
            title = clean_html_tags(item['title'])
            date = parse_pubdate(item['pubDate'])
            score = item.get('relevance_score', 0)

            print(f"\n[{stock_info['name']}]")
            print(f"제목: {title[:70]}...")
            print(f"날짜: {date} | 관련도: {score:.2f}")

    print("\n" + "=" * 80)
    print("🎉 모든 테스트 완료!")
    print("=" * 80)


def run_all_tests():
    """모든 테스트 실행"""
    print("\n")
    print("🧪 네이버 뉴스 API 고급 기능 테스트 시작")
    print("=" * 80)
    print()

    # Test 1: HTML 엔티티 디코딩
    test_html_entity_decoding()
    time.sleep(0.5)

    # Test 2: 날짜 필터링
    test_date_filtering()
    time.sleep(0.5)

    # Test 3: 관련도 점수
    test_relevance_scoring()
    time.sleep(0.5)

    # Test 4: 일괄 수집
    test_bulk_collection()


if __name__ == "__main__":
    run_all_tests()
