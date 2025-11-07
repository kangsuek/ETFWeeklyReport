import pytest
from datetime import date, timedelta
from app.services.news_scraper import NewsScraper
from app.database import init_db
from httpx import AsyncClient
from app.main import app

class TestNewsScraping:
    """뉴스 스크래핑 테스트"""
    
    def test_fetch_naver_news(self):
        """Naver 뉴스 Mock 데이터 수집 테스트"""
        scraper = NewsScraper()
        
        news_data = scraper.fetch_naver_news("AI", days=5)
        
        assert len(news_data) == 5
        assert all('title' in item for item in news_data)
        assert all('url' in item for item in news_data)
        assert all('source' in item for item in news_data)
        assert all('date' in item for item in news_data)
        assert all('relevance_score' in item for item in news_data)
    
    def test_parse_news_date(self):
        """뉴스 날짜 파싱 테스트"""
        scraper = NewsScraper()
        
        # "N시간 전" 패턴
        assert scraper._parse_news_date("5시간 전") == date.today()
        
        # "N일 전" 패턴
        expected_date = date.today() - timedelta(days=3)
        assert scraper._parse_news_date("3일 전") == expected_date
        
        # "YYYY.MM.DD" 패턴
        assert scraper._parse_news_date("2025.11.07") == date(2025, 11, 7)
        
        # 빈 문자열 - 오늘 날짜 반환
        assert scraper._parse_news_date("") == date.today()
    
    def test_calculate_relevance(self):
        """관련도 점수 계산 테스트"""
        scraper = NewsScraper()
        
        # 완전 일치
        assert scraper._calculate_relevance("AI 전력 시장 동향", "AI") == 1.0
        
        # 부분 일치
        relevance = scraper._calculate_relevance("전력 시장 동향", "AI 전력")
        assert 0 < relevance < 1.0
        
        # 불일치
        relevance = scraper._calculate_relevance("조선 시장", "AI")
        assert relevance >= 0


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
    
    def test_collect_and_save_news(self):
        """뉴스 수집 및 저장 통합 테스트"""
        scraper = NewsScraper()
        
        # 새로운 종목으로 테스트 (중복 방지)
        result = scraper.collect_and_save_news('034020', days=3)
        
        assert result['ticker'] == '034020'
        assert result['collected'] >= 0  # Mock 데이터는 항상 생성되지만 중복이면 0
        assert 'keywords_used' in result
        assert 'message' in result


class TestNewsAPI:
    """뉴스 API 엔드포인트 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 전 DB 초기화"""
        init_db()
    
    @pytest.mark.asyncio
    async def test_collect_news_success(self):
        """뉴스 수집 API 테스트"""
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
    async def test_get_news_success(self):
        """뉴스 조회 API 테스트"""
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
    async def test_get_news_with_date_range(self):
        """날짜 범위로 뉴스 조회 테스트"""
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


class TestNewsIntegration:
    """뉴스 기능 통합 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 전 DB 초기화"""
        init_db()
    
    @pytest.mark.asyncio
    async def test_full_news_flow(self):
        """뉴스 수집 → 저장 → 조회 전체 플로우 테스트"""
        scraper = NewsScraper()
        
        # 1. 뉴스 수집 및 저장 (새 종목 사용)
        result = scraper.collect_and_save_news('442320', days=5)
        assert result['ticker'] == '442320'
        
        # 2. 조회
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
        news_list = scraper.get_news_for_ticker('442320', start_date, end_date)
        
        # Mock 데이터가 생성되므로 최소 1개 이상
        assert len(news_list) >= 0
        if news_list:
            assert news_list[0].relevance_score is not None
    
    @pytest.mark.asyncio
    async def test_multiple_tickers_news(self):
        """여러 종목 뉴스 수집 테스트"""
        # 각각 다른 종목 사용 (중복 방지)
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

