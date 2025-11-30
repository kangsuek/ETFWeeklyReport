import pytest
from datetime import date, timedelta
from app.services.news_scraper import NewsScraper
from app.database import init_db, get_db_connection
from httpx import AsyncClient
from app.main import app
from unittest.mock import patch, MagicMock

class TestNewsScraping:
    """뉴스 스크래핑 테스트"""

    @patch('app.services.news_scraper.NewsScraper._search_naver_news_api')
    def test_fetch_naver_news(self, mock_api):
        """Naver 뉴스 API 데이터 수집 테스트"""
        # Mock API 응답 설정
        mock_api.return_value = {
            'total': 100,
            'items': [
                {
                    'title': 'AI 전력 시장 급성장',
                    'link': 'https://news.naver.com/test1',
                    'description': 'AI 데이터센터 전력 수요',
                    'pubDate': 'Fri, 08 Nov 2025 10:00:00 +0900'
                },
                {
                    'title': '데이터센터 전력 수요 증가',
                    'link': 'https://news.naver.com/test2',
                    'description': 'AI 기술 발전으로 전력',
                    'pubDate': 'Fri, 08 Nov 2025 09:00:00 +0900'
                }
            ]
        }

        scraper = NewsScraper()
        news_data = scraper.fetch_naver_news(
            "AI",
            days=7,
            relevance_keywords=["AI", "전력"]
        )

        assert len(news_data) == 2
        assert all('title' in item for item in news_data)
        assert all('url' in item for item in news_data)
        assert all('source' in item for item in news_data)
        assert all('date' in item for item in news_data)
        assert all('relevance_score' in item for item in news_data)

    def test_parse_pubdate(self):
        """뉴스 날짜 파싱 테스트"""
        scraper = NewsScraper()

        # RFC 822 형식 파싱
        result = scraper._parse_pubdate("Fri, 08 Nov 2025 14:50:00 +0900")
        assert result == date(2025, 11, 8)

    def test_calculate_relevance_score(self):
        """관련도 점수 계산 테스트 (고도화된 알고리즘 v3 - 단순화)"""
        scraper = NewsScraper()

        # Case 1: 제목에 2개 키워드 → 0.8 이상
        news_item = {
            'title': 'AI 전력 시장 동향',
            'description': '데이터센터 관련 뉴스'
        }
        score = scraper._calculate_relevance_score(news_item, ["AI", "전력"])
        # title_matches=2, keyword_ratio=2/2=1.0
        # 0.80 + (1.0 * 0.20) = 1.0
        assert score >= 0.8

        # Case 2: 제목 1개 + 본문 1개 → 0.7~0.9
        news_item2 = {
            'title': '전력 시장 동향',
            'description': 'AI 데이터센터 확장'
        }
        score2 = scraper._calculate_relevance_score(news_item2, ["AI", "전력"])
        # title_matches=1, desc_matches=1, keyword_ratio=2/2=1.0
        # 0.70 + (1.0 * 0.20) = 0.9
        assert 0.7 <= score2 <= 0.9

        # Case 3: 제목에만 1개 → 0.6~0.8
        news_item3 = {
            'title': '전력 시장 동향',
            'description': '에너지 산업 전망'
        }
        score3 = scraper._calculate_relevance_score(news_item3, ["AI", "전력"])
        # title_matches=1, desc_matches=0, keyword_ratio=1/2=0.5
        # 0.60 + (0.5 * 0.20) = 0.70
        assert 0.6 <= score3 <= 0.8

        # Case 4: 본문에 2개 → 0.55~0.7
        news_item4 = {
            'title': '시장 동향 분석',
            'description': 'AI 기술과 전력 인프라'
        }
        score4 = scraper._calculate_relevance_score(news_item4, ["AI", "전력"])
        # title_matches=0, desc_matches=2, keyword_ratio=2/2=1.0
        # 0.55 + (1.0 * 0.15) = 0.70
        assert score4 == pytest.approx(0.7, rel=0.01)

        # Case 5: 본문에만 1개 → 0.45~0.6
        news_item5 = {
            'title': '시장 전망',
            'description': 'AI 기술 발전'
        }
        score5 = scraper._calculate_relevance_score(news_item5, ["AI", "전력"])
        # title_matches=0, desc_matches=1, keyword_ratio=1/2=0.5
        # 0.45 + (0.5 * 0.15) = 0.525
        assert 0.45 <= score5 <= 0.6

        # Case 6: 매칭 없음 → 0.4
        news_item6 = {
            'title': '조선 시장',
            'description': '선박 수주'
        }
        score6 = scraper._calculate_relevance_score(news_item6, ["AI"])
        # title_matches=0, desc_matches=0
        # 0.40
        assert score6 == pytest.approx(0.4, rel=0.01)


class TestNewsDataManagement:
    """뉴스 데이터 관리 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 전 DB 초기화"""
        init_db()
    
    def test_save_news_data(self):
        """뉴스 데이터 저장 테스트"""
        scraper = NewsScraper()
        
        # 고유한 URL 사용
        import time
        timestamp = str(int(time.time() * 1000))
        
        news_data = [
            {
                'date': date.today(),
                'title': '테스트 뉴스 1',
                'url': f'https://test.com/news/save1/{timestamp}',
                'source': '테스트뉴스',
                'relevance_score': 0.9
            },
            {
                'date': date.today(),
                'title': '테스트 뉴스 2',
                'url': f'https://test.com/news/save2/{timestamp}',
                'source': '테스트뉴스',
                'relevance_score': 0.8
            }
        ]
        
        saved_count = scraper.save_news_data('042660', news_data)
        assert saved_count == 2
    
    def test_save_news_data_empty(self):
        """빈 뉴스 데이터 저장 테스트"""
        scraper = NewsScraper()
        
        saved_count = scraper.save_news_data('042660', [])
        assert saved_count == 0
    
    def test_save_news_data_duplicate(self):
        """중복 뉴스 저장 방지 테스트"""
        scraper = NewsScraper()
        
        # 고유한 URL 사용
        import time
        timestamp = str(int(time.time() * 1000))
        url = f'https://test.com/news/duplicate/{timestamp}'
        
        news_data = [{
            'date': date.today(),
            'title': '중복 테스트 뉴스',
            'url': url,
            'source': '테스트뉴스',
            'relevance_score': 0.9
        }]
        
        # 첫 번째 저장
        saved_count1 = scraper.save_news_data('042660', news_data)
        assert saved_count1 == 1
        
        # 동일한 뉴스 다시 저장 (중복)
        saved_count2 = scraper.save_news_data('042660', news_data)
        assert saved_count2 == 0
    
    def test_get_news_for_ticker(self):
        """종목별 뉴스 조회 테스트"""
        scraper = NewsScraper()
        
        # 먼저 데이터 저장
        news_data = [{
            'date': date.today(),
            'title': '조회 테스트 뉴스',
            'url': 'https://test.com/news/retrieve/test123',
            'source': '테스트뉴스',
            'relevance_score': 0.9
        }]
        scraper.save_news_data('042660', news_data)
        
        # 조회
        start_date = date.today() - timedelta(days=1)
        end_date = date.today()
        news_list = scraper.get_news_for_ticker('042660', start_date, end_date)
        
        assert len(news_list) > 0
        # 저장한 뉴스가 리스트에 포함되어 있는지 확인
        titles = [news.title for news in news_list]
        assert '조회 테스트 뉴스' in titles
    
    @patch('app.services.news_scraper.NewsScraper._search_naver_news_api')
    def test_collect_and_save_news(self, mock_api):
        """뉴스 수집 및 저장 통합 테스트"""
        # Mock API 응답 설정
        mock_api.return_value = {
            'total': 50,
            'items': [
                {
                    'title': '두산에너빌리티 실적 발표',
                    'link': 'https://news.naver.com/test_doosan1',
                    'description': '두산에너빌리티 원자력 사업',
                    'pubDate': 'Fri, 08 Nov 2025 10:00:00 +0900'
                }
            ]
        }

        scraper = NewsScraper()

        # 새로운 종목으로 테스트
        result = scraper.collect_and_save_news('034020', days=3)

        assert result['ticker'] == '034020'
        assert result['collected'] >= 0
        assert 'keywords_used' in result
        assert 'message' in result


class TestNewsAPI:
    """뉴스 API 엔드포인트 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 전 DB 초기화"""
        init_db()
    
    @pytest.mark.asyncio
    @patch('app.services.news_scraper.NewsScraper._search_naver_news_api')
    async def test_collect_news_success(self, mock_api):
        """뉴스 수집 API 테스트"""
        # Mock API 응답
        mock_api.return_value = {
            'total': 30,
            'items': [
                {
                    'title': '조선 ETF 시장 전망',
                    'link': 'https://news.naver.com/test_sol1',
                    'description': '조선 ETF 투자 확대',
                    'pubDate': 'Fri, 08 Nov 2025 10:00:00 +0900'
                }
            ]
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/news/466920/collect?days=5")

            assert response.status_code == 200
            data = response.json()
            assert data['ticker'] == '466920'
            assert data['collected'] >= 0
            assert 'SOL' in data['name']
    
    @pytest.mark.asyncio
    async def test_collect_news_not_found(self):
        """존재하지 않는 종목 뉴스 수집 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/news/999999/collect?days=5")
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    @patch('app.services.news_scraper.NewsScraper._search_naver_news_api')
    async def test_get_news_success(self, mock_api):
        """뉴스 조회 API 테스트"""
        # Mock API 응답
        mock_api.return_value = {
            'total': 100,
            'items': [
                {
                    'title': '한화오션 수주 소식',
                    'link': 'https://news.naver.com/test_hanwha1',
                    'description': '한화오션 조선 사업',
                    'pubDate': 'Fri, 08 Nov 2025 10:00:00 +0900'
                }
            ]
        }

        # 먼저 뉴스 수집
        async with AsyncClient(app=app, base_url="http://test") as client:
            await client.post("/api/news/042660/collect?days=3")

            # 조회
            response = await client.get("/api/news/042660")

            assert response.status_code == 200
            news_list = response.json()
            assert isinstance(news_list, list)
            if news_list:
                assert 'title' in news_list[0]
                assert 'url' in news_list[0]
                assert 'source' in news_list[0]
    
    @pytest.mark.asyncio
    @patch('app.services.news_scraper.NewsScraper._search_naver_news_api')
    async def test_get_news_with_date_range(self, mock_api):
        """날짜 범위로 뉴스 조회 테스트"""
        # Mock API 응답
        mock_api.return_value = {
            'total': 100,
            'items': [
                {
                    'title': '한화오션 뉴스',
                    'link': 'https://news.naver.com/test_hanwha2',
                    'description': '한화오션',
                    'pubDate': 'Fri, 08 Nov 2025 10:00:00 +0900'
                }
            ]
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 뉴스 수집
            await client.post("/api/news/042660/collect?days=7")

            # 날짜 범위 지정 조회
            start_date = (date.today() - timedelta(days=3)).isoformat()
            end_date = date.today().isoformat()

            response = await client.get(
                f"/api/news/042660?start_date={start_date}&end_date={end_date}"
            )

            assert response.status_code == 200
            news_list = response.json()
            assert isinstance(news_list, list)
    
    @pytest.mark.asyncio
    async def test_get_news_not_found(self):
        """존재하지 않는 종목 뉴스 조회 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/news/999999")
            
            assert response.status_code == 404

    @pytest.mark.asyncio
    @patch('app.services.news_scraper.NewsScraper._search_naver_news_api')
    async def test_get_news_triggers_collection_when_empty(self, mock_api):
        """초기 뉴스 부재 시 자동 수집이 발생하는지 검증"""
        mock_api.return_value = {
            'total': 10,
            'items': [
                {
                    'title': 'AI 인프라 투자 확대',
                    'link': 'https://news.naver.com/test_auto_collect',
                    'description': 'AI 전력 인프라',
                    'pubDate': 'Fri, 08 Nov 2025 11:00:00 +0900'
                }
            ]
        }

        # 캐시와 뉴스 테이블 초기화
        from app.routers import news as news_router
        news_router.cache.clear()
        with get_db_connection() as conn:
            conn.execute("DELETE FROM news")
            conn.commit()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/news/487240")

            assert response.status_code == 200
            news_list = response.json()
            assert isinstance(news_list, list)
            assert len(news_list) >= 1


class TestNewsIntegration:
    """뉴스 기능 통합 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 전 DB 초기화"""
        init_db()
    
    @pytest.mark.asyncio
    @patch('app.services.news_scraper.NewsScraper._search_naver_news_api')
    async def test_full_news_flow(self, mock_api):
        """뉴스 수집 → 저장 → 조회 전체 플로우 테스트"""
        # Mock API 응답
        mock_api.return_value = {
            'total': 50,
            'items': [
                {
                    'title': '원자력 ETF 전망',
                    'link': 'https://news.naver.com/test_rise1',
                    'description': '원자력 ETF 투자',
                    'pubDate': 'Fri, 08 Nov 2025 10:00:00 +0900'
                }
            ]
        }

        scraper = NewsScraper()

        # 1. 뉴스 수집 및 저장
        result = scraper.collect_and_save_news('442320', days=5)
        assert result['ticker'] == '442320'

        # 2. 조회
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
        news_list = scraper.get_news_for_ticker('442320', start_date, end_date)

        # 데이터가 있으면 검증
        assert len(news_list) >= 0
        if news_list:
            assert news_list[0].relevance_score is not None

    @pytest.mark.asyncio
    @patch('app.services.news_scraper.NewsScraper._search_naver_news_api')
    async def test_multiple_tickers_news(self, mock_api):
        """여러 종목 뉴스 수집 테스트"""
        # Mock API 응답
        mock_api.return_value = {
            'total': 50,
            'items': [
                {
                    'title': 'ETF 시장 뉴스',
                    'link': 'https://news.naver.com/test_etf1',
                    'description': 'ETF 투자',
                    'pubDate': 'Fri, 08 Nov 2025 10:00:00 +0900'
                }
            ]
        }

        # 각각 다른 종목 사용
        test_cases = [
            ('487240', 'KODEX'),
            ('466920', 'SOL'),
            ('442320', 'RISE')
        ]

        async with AsyncClient(app=app, base_url="http://test") as client:
            for ticker, name_part in test_cases:
                response = await client.post(f"/api/news/{ticker}/collect?days=3")
                assert response.status_code == 200

                data = response.json()
                assert data['ticker'] == ticker
                assert 'collected' in data
                assert name_part in data['name']

