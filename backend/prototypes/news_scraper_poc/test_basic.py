"""
네이버 뉴스 API 기본 테스트
Basic Test for Naver News API
"""

import time
from naver_news_api import search_news, clean_html_tags, parse_pubdate


def test_search_news():
    """
    단일 키워드로 뉴스 검색 테스트
    """
    print("=" * 50)
    print("네이버 뉴스 API 테스트")
    print("=" * 50)

    keyword = "AI"
    start_time = time.time()

    try:
        # API 호출
        result = search_news(keyword, display=10, sort="date")
        elapsed_time = time.time() - start_time

        # 기본 정보 출력
        print(f"검색 키워드: {keyword}")
        print(f"검색 결과: {len(result['items'])}건 / 전체 {result['total']:,}건")
        print(f"응답 시간: {elapsed_time:.2f}초")
        print("=" * 50)
        print()

        # 각 뉴스 아이템 출력
        for i, item in enumerate(result['items'], 1):
            # HTML 태그 제거 및 날짜 파싱
            title_clean = clean_html_tags(item['title'])
            description_clean = clean_html_tags(item['description'])
            date_formatted = parse_pubdate(item['pubDate'])

            print(f"[{i}] 제목: {title_clean}")
            print(f"    URL: {item['link']}")
            print(f"    원본 URL: {item['originallink']}")
            print(f"    날짜: {date_formatted}")
            print(f"    요약: {description_clean[:100]}...")
            print()

        # 검증 항목
        print("=" * 50)
        print("검증 결과")
        print("=" * 50)

        # 1. 결과 개수 확인
        assert len(result['items']) == 10, f"❌ 결과 개수 불일치: {len(result['items'])} != 10"
        print("✅ 결과 개수: 10건")

        # 2. 필수 필드 확인
        required_fields = ['title', 'link', 'originallink', 'description', 'pubDate']
        for field in required_fields:
            assert field in result['items'][0], f"❌ {field} 필드 없음"
        print(f"✅ 필수 필드 존재: {', '.join(required_fields)}")

        # 3. 응답 시간 확인
        assert elapsed_time < 2.0, f"❌ 응답 시간 초과: {elapsed_time:.2f}초 > 2초"
        print(f"✅ 응답 시간: {elapsed_time:.2f}초 < 2초")

        # 4. HTML 태그 제거 확인
        has_html_tag = '<' in title_clean or '>' in title_clean
        assert not has_html_tag, "❌ HTML 태그가 제거되지 않음"
        print("✅ HTML 태그 제거 성공")

        # 5. 날짜 파싱 확인
        assert len(date_formatted) == 10, f"❌ 날짜 형식 오류: {date_formatted}"
        assert date_formatted.count('-') == 2, f"❌ 날짜 형식 오류: {date_formatted}"
        print(f"✅ 날짜 파싱 성공: YYYY-MM-DD 형식")

        print("=" * 50)
        print("🎉 모든 테스트 통과!")
        print("=" * 50)

        return result

    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        raise


if __name__ == "__main__":
    result = test_search_news()
