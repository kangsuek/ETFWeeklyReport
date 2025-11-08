"""
네이버 뉴스 검색 API 기본 구현
Naver News Search API Implementation
"""

import os
import re
import html
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")


def search_news(
    query: str,
    display: int = 10,
    start: int = 1,
    sort: str = "date"
) -> Dict:
    """
    네이버 뉴스 검색 API 호출

    Args:
        query: 검색 키워드 (UTF-8)
        display: 검색 결과 개수 (1-100)
        start: 검색 시작 위치 (1-1000)
        sort: 정렬 방식 (sim: 정확도, date: 날짜)

    Returns:
        dict: API 응답 JSON

    Raises:
        requests.exceptions.RequestException: API 호출 실패
    """
    url = "https://openapi.naver.com/v1/search/news.json"

    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }

    params = {
        "query": query,
        "display": display,
        "start": start,
        "sort": sort
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            print("❌ 인증 실패: Client ID/Secret 확인")
        elif response.status_code == 403:
            print("❌ API 권한 없음: 개발자 센터에서 검색 API 활성화 필요")
        elif response.status_code == 429:
            print("❌ Rate Limit 초과: 일일 한도 25,000회 확인")
        else:
            print(f"❌ HTTP 에러: {e}")
        raise
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        raise


def clean_html_tags(text: str) -> str:
    """
    HTML 태그 및 엔티티 제거

    Args:
        text: HTML 태그가 포함된 문자열

    Returns:
        str: 태그가 제거된 순수 텍스트
    """
    # <b>, </b> 등 모든 HTML 태그 제거
    clean_text = re.sub(r'<[^>]+>', '', text)
    # HTML 엔티티 디코딩 (&quot; → ", &amp; → & 등)
    clean_text = html.unescape(clean_text)
    return clean_text


def parse_pubdate(pubdate_str: str) -> str:
    """
    pubDate를 YYYY-MM-DD 형식으로 변환

    Args:
        pubdate_str: "Mon, 08 Nov 2025 14:50:00 +0900" 형식

    Returns:
        str: "2025-11-08" 형식
    """
    # RFC 822 형식 파싱
    dt = datetime.strptime(pubdate_str, "%a, %d %b %Y %H:%M:%S %z")
    return dt.strftime("%Y-%m-%d")


def parse_pubdate_to_datetime(pubdate_str: str) -> datetime:
    """
    pubDate를 datetime 객체로 변환

    Args:
        pubdate_str: "Mon, 08 Nov 2025 14:50:00 +0900" 형식

    Returns:
        datetime: datetime 객체
    """
    return datetime.strptime(pubdate_str, "%a, %d %b %Y %H:%M:%S %z")


def filter_by_date_range(news_items: List[Dict], days: int = 7) -> List[Dict]:
    """
    날짜 범위로 뉴스 필터링 (최근 N일 이내)

    Args:
        news_items: 뉴스 아이템 리스트
        days: 필터링할 일수 (기본값: 7일)

    Returns:
        list: 필터링된 뉴스 리스트
    """
    cutoff_date = datetime.now(tz=None).replace(tzinfo=None) - timedelta(days=days)
    filtered = []

    for item in news_items:
        pub_dt = parse_pubdate_to_datetime(item['pubDate'])
        # timezone-naive로 변환하여 비교
        pub_dt_naive = pub_dt.replace(tzinfo=None)

        if pub_dt_naive >= cutoff_date:
            filtered.append(item)

    return filtered


def calculate_relevance_score(news_item: Dict, keywords: List[str]) -> float:
    """
    뉴스 아이템의 관련도 점수 계산

    Args:
        news_item: 뉴스 아이템 (title, description 포함)
        keywords: 검색 키워드 리스트

    Returns:
        float: 관련도 점수 (0.0 ~ 1.0)
    """
    title = clean_html_tags(news_item.get('title', '')).lower()
    description = clean_html_tags(news_item.get('description', '')).lower()

    score = 0.0
    max_score = len(keywords) * 2  # 제목 1점, 본문 1점

    for keyword in keywords:
        keyword_lower = keyword.lower()

        # 제목에 키워드 포함: 1점
        if keyword_lower in title:
            score += 1.0

        # 본문에 키워드 포함: 1점
        if keyword_lower in description:
            score += 1.0

    # 정규화 (0.0 ~ 1.0)
    return score / max_score if max_score > 0 else 0.0


def search_news_with_filters(
    query: str,
    display: int = 10,
    days: int = 7,
    min_relevance: float = 0.0,
    keywords: Optional[List[str]] = None
) -> List[Dict]:
    """
    필터링이 적용된 뉴스 검색

    Args:
        query: 검색 키워드
        display: 검색 결과 개수 (1-100)
        days: 날짜 필터링 (최근 N일)
        min_relevance: 최소 관련도 점수 (0.0 ~ 1.0)
        keywords: 관련도 계산용 키워드 리스트

    Returns:
        list: 필터링된 뉴스 리스트
    """
    # API 호출
    result = search_news(query, display=display, sort="date")
    news_items = result.get('items', [])

    # 날짜 필터링
    if days > 0:
        news_items = filter_by_date_range(news_items, days=days)

    # 관련도 필터링
    if keywords and min_relevance > 0.0:
        filtered_items = []
        for item in news_items:
            score = calculate_relevance_score(item, keywords)
            if score >= min_relevance:
                item['relevance_score'] = score
                filtered_items.append(item)
        news_items = filtered_items
    elif keywords:
        # 관련도 점수만 추가
        for item in news_items:
            item['relevance_score'] = calculate_relevance_score(item, keywords)

    return news_items


# 대상 종목 정의
TARGET_STOCKS = [
    {
        "name": "삼성 KODEX AI전력핵심설비 ETF",
        "code": "487240",
        "search_keyword": "AI 전력",
        "relevance_keywords": ["AI", "전력", "데이터센터"],
        "category": "ETF"
    },
    {
        "name": "신한 SOL 조선TOP3플러스 ETF",
        "code": "466920",
        "search_keyword": "조선 ETF",
        "relevance_keywords": ["조선", "ETF", "한화오션", "HD현대중공업"],
        "category": "ETF"
    },
    {
        "name": "KoAct 글로벌양자컴퓨팅액티브 ETF",
        "code": "0020H0",
        "search_keyword": "양자컴퓨팅 ETF",
        "relevance_keywords": ["양자컴퓨팅", "ETF"],
        "category": "ETF"
    },
    {
        "name": "KB RISE 글로벌원자력 iSelect ETF",
        "code": "442320",
        "search_keyword": "원자력 ETF",
        "relevance_keywords": ["원자력", "ETF", "SMR"],
        "category": "ETF"
    },
    {
        "name": "한화오션",
        "code": "042660",
        "search_keyword": "한화오션",
        "relevance_keywords": ["한화오션", "조선", "방산"],
        "category": "주식"
    },
    {
        "name": "두산에너빌리티",
        "code": "034020",
        "search_keyword": "두산에너빌리티",
        "relevance_keywords": ["두산에너빌리티", "원자력", "에너지"],
        "category": "주식"
    }
]


def collect_all_stock_news(
    display_per_stock: int = 10,
    days: int = 7,
    min_relevance: float = 0.0,
    rate_limit_delay: float = 0.1
) -> Dict[str, List[Dict]]:
    """
    6개 종목 전체에 대한 뉴스 일괄 수집

    Args:
        display_per_stock: 종목당 수집할 뉴스 개수
        days: 날짜 필터링 (최근 N일)
        min_relevance: 최소 관련도 점수
        rate_limit_delay: API 호출 간격 (초)

    Returns:
        dict: {종목코드: [뉴스 리스트]} 형태
    """
    results = {}

    for stock in TARGET_STOCKS:
        code = stock['code']
        query = stock['search_keyword']
        keywords = stock['relevance_keywords']

        print(f"📰 [{stock['category']}] {stock['name']} 뉴스 수집 중...")

        try:
            news_items = search_news_with_filters(
                query=query,
                display=display_per_stock,
                days=days,
                min_relevance=min_relevance,
                keywords=keywords
            )

            # 메타데이터 추가
            for item in news_items:
                item['stock_code'] = code
                item['stock_name'] = stock['name']
                item['category'] = stock['category']

            results[code] = news_items
            print(f"   ✅ {len(news_items)}건 수집 완료")

        except Exception as e:
            print(f"   ❌ 에러: {e}")
            results[code] = []

        # Rate Limiting
        time.sleep(rate_limit_delay)

    return results


if __name__ == "__main__":
    # 기본 테스트
    print("네이버 뉴스 API 기본 테스트")
    print("=" * 50)

    result = search_news("AI", display=5)
    print(f"검색 결과: {result['total']:,}건")
    print(f"수집된 뉴스: {len(result['items'])}건")
    print()

    for i, item in enumerate(result['items'], 1):
        title_clean = clean_html_tags(item['title'])
        date_formatted = parse_pubdate(item['pubDate'])
        print(f"[{i}] {title_clean}")
        print(f"    날짜: {date_formatted}")
        print()
