"""
뉴스 분석 서비스

뉴스의 센티먼트, 태그, 요약을 분석하는 서비스
키워드 기반 규칙 분석 방식 사용
"""

from typing import List, Dict, Optional
import re
import logging

logger = logging.getLogger(__name__)

# 센티먼트 키워드 정의
SENTIMENT_KEYWORDS = {
    'positive': [
        '급등', '상승', '호재', '실적개선', '수주', '신고가', '돌파',
        '상향', '호황', '반등', '성장', '확대', '증가', '개선',
        '기대감', '강세', '최대', '흑자', '회복', '주목', '수익',
        '성공', '확장', '투자', '협력', '계약', '발표', '출시'
    ],
    'negative': [
        '급락', '하락', '악재', '실적부진', '규제', '리스크', '우려',
        '하향', '불황', '위축', '감소', '악화', '폭락', '조정',
        '불안', '약세', '적자', '손실', '위기', '충격', '부진',
        '감소', '축소', '중단', '취소', '거부', '반대', '비판'
    ]
}

# 토픽 키워드 정의
TOPIC_KEYWORDS = {
    '정책': ['규제', '관세', '정책', '제재', '법안', '정부', '금지', '승인', '조치', '법률'],
    '업황': ['수요', '출하량', '가격', '반등', '전망', '사이클', '업황', '시황', '수급', '시장'],
    '실적': ['실적', '매출', '영업이익', '분기', '예상치', '순이익', '성장률', '어닝', '분기실적'],
    '기업': ['삼성', 'SK', '하이닉스', '인수', '합병', '투자', '신규', '설비', '증설', '기업'],
    '금리': ['금리', '인상', '인하', '연준', '기준금리', 'Fed', '통화정책', '금융'],
    '환율': ['환율', '달러', '원화', '엔화', '강세', '약세', '외환', '환전'],
    '반도체': ['반도체', '칩', '메모리', 'D램', '낸드', '팹', '웨이퍼', 'TSMC'],
    '관세': ['관세', '수출규제', '수입규제', '무역', '보복관세', '미국', '중국']
}


class NewsAnalyzer:
    """뉴스 분석 서비스 클래스"""

    @staticmethod
    def count_keywords(text: str, keywords: List[str]) -> int:
        """
        텍스트에서 키워드 출현 횟수 계산

        Args:
            text: 검색 대상 텍스트
            keywords: 검색할 키워드 배열

        Returns:
            키워드 출현 횟수
        """
        if not text or not keywords:
            return 0

        count = 0
        text_lower = text.lower()
        for keyword in keywords:
            # 대소문자 구분 없이 검색
            pattern = re.compile(re.escape(keyword.lower()), re.IGNORECASE)
            matches = pattern.findall(text_lower)
            count += len(matches)

        return count

    @staticmethod
    def analyze_sentiment(title: str) -> str:
        """
        개별 뉴스 센티먼트 분석

        Args:
            title: 뉴스 제목

        Returns:
            'positive' | 'negative' | 'neutral'
        """
        if not title:
            return 'neutral'

        positive_count = NewsAnalyzer.count_keywords(title, SENTIMENT_KEYWORDS['positive'])
        negative_count = NewsAnalyzer.count_keywords(title, SENTIMENT_KEYWORDS['negative'])

        if positive_count > negative_count:
            return 'positive'
        if negative_count > positive_count:
            return 'negative'
        return 'neutral'

    @staticmethod
    def extract_tags(title: str, max_tags: int = 2) -> List[str]:
        """
        개별 뉴스 토픽 태그 추출

        Args:
            title: 뉴스 제목
            max_tags: 최대 태그 개수

        Returns:
            토픽 태그 배열
        """
        if not title:
            return []

        topic_counts = []
        for topic, keywords in TOPIC_KEYWORDS.items():
            count = NewsAnalyzer.count_keywords(title, keywords)
            if count > 0:
                topic_counts.append({
                    'topic': topic,
                    'count': count
                })

        # 카운트가 높은 순으로 정렬하고 상위 N개만 선택
        topic_counts.sort(key=lambda x: x['count'], reverse=True)
        return [t['topic'] for t in topic_counts[:max_tags]]

    @staticmethod
    def generate_summary(news_list: List[Dict], topics: List[str], sentiment: str) -> Optional[str]:
        """
        뉴스 요약 문장 생성

        Args:
            news_list: 뉴스 리스트
            topics: 주요 토픽 배열
            sentiment: 전체 센티먼트

        Returns:
            요약 문장 또는 None
        """
        if not topics or len(news_list) == 0:
            return None

        sentiment_text = {
            'positive': '긍정적인',
            'negative': '부정적인',
            'neutral': ''
        }.get(sentiment, '')

        topics_text = ', '.join(topics)
        count = len(news_list)

        if sentiment_text:
            return f"최근 {count}건의 뉴스는 {topics_text} 관련 {sentiment_text} 소식에 집중되어 있습니다."
        return f"최근 {count}건의 뉴스는 {topics_text} 관련 소식이 주를 이루고 있습니다."

    @staticmethod
    def analyze_news_list(news_list: List[Dict]) -> Dict:
        """
        뉴스 목록 전체 분석

        Args:
            news_list: 뉴스 배열 [{title, ...}, ...]

        Returns:
            {
                'sentiment': 'positive' | 'negative' | 'neutral',
                'topics': List[str],
                'summary': Optional[str],
                'analyzed_news': List[Dict]  # 각 뉴스에 sentiment, tags 추가
            }
        """
        if not news_list or len(news_list) == 0:
            return {
                'sentiment': 'neutral',
                'topics': [],
                'summary': None,
                'analyzed_news': []
            }

        # 모든 뉴스 제목 합치기
        all_titles = ' '.join([news.get('title', '') for news in news_list])

        # 전체 센티먼트 분석
        positive_count = NewsAnalyzer.count_keywords(all_titles, SENTIMENT_KEYWORDS['positive'])
        negative_count = NewsAnalyzer.count_keywords(all_titles, SENTIMENT_KEYWORDS['negative'])

        overall_sentiment = 'neutral'
        if positive_count > negative_count + 2:
            overall_sentiment = 'positive'
        elif negative_count > positive_count + 2:
            overall_sentiment = 'negative'

        # 주요 토픽 추출
        topic_counts = []
        for topic, keywords in TOPIC_KEYWORDS.items():
            count = NewsAnalyzer.count_keywords(all_titles, keywords)
            if count > 0:
                topic_counts.append({
                    'topic': topic,
                    'count': count
                })

        # 카운트가 높은 순으로 정렬하고 상위 3개만 선택
        topic_counts.sort(key=lambda x: x['count'], reverse=True)
        topics = [t['topic'] for t in topic_counts[:3]]

        # 개별 뉴스 분석
        analyzed_news = []
        for news in news_list:
            title = news.get('title', '')
            analyzed_news.append({
                **news,
                'sentiment': NewsAnalyzer.analyze_sentiment(title),
                'tags': NewsAnalyzer.extract_tags(title, max_tags=2)
            })

        # 요약 문장 생성
        summary = NewsAnalyzer.generate_summary(news_list, topics, overall_sentiment)

        return {
            'sentiment': overall_sentiment,
            'topics': topics,
            'summary': summary,
            'analyzed_news': analyzed_news
        }
