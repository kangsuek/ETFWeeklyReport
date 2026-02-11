"""
스케줄러 서비스 모듈

APScheduler를 사용하여 정기적인 데이터 수집 작업을 스케줄링합니다.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import pytz

from app.config import Config
from app.services.data_collector import ETFDataCollector
from app.services.news_scraper import NewsScraper
from app.services.ticker_catalog_collector import TickerCatalogCollector
from app.services.catalog_data_collector import CatalogDataCollector

# 로거 설정
logger = logging.getLogger(__name__)

# 한국 시간대
KST = pytz.timezone('Asia/Seoul')

# 스케줄러 인스턴스
scheduler = None


class DataCollectionScheduler:
    """데이터 수집 스케줄러 클래스"""

    def __init__(self):
        """스케줄러 초기화"""
        self.scheduler = AsyncIOScheduler(timezone=KST)
        self.collector = ETFDataCollector()
        self.news_scraper = NewsScraper()
        self.ticker_catalog_collector = TickerCatalogCollector()
        self.catalog_data_collector = CatalogDataCollector()
        self._jobs = {}
        self.last_collection_time = None
        self.is_collecting = False
        self.last_catalog_collection_time = None
        self.last_catalog_data_collection_time = None
        logger.info("DataCollectionScheduler 초기화 완료")
    
    def collect_periodic_data(self):
        """
        주기적 데이터 수집 작업 (가격, 매매동향, 뉴스)

        설정된 주기(SCRAPING_INTERVAL_MINUTES)마다 모든 종목의 실시간 데이터를 수집합니다.
        """
        if self.is_collecting:
            logger.warning("[스케줄러-주기수집] 이미 수집 작업이 진행 중입니다. 건너뜁니다.")
            return

        self.is_collecting = True
        start_time = datetime.now(KST)
        logger.info(f"[스케줄러-주기수집] 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            tickers = Config.get_all_tickers()
            total_tickers = len(tickers)
            success_count = 0
            error_count = 0
            total_price_records = 0
            total_trading_records = 0
            total_news_records = 0

            for ticker in tickers:
                try:
                    stock_info = Config.get_stock_info(ticker)
                    stock_name = stock_info.get('name', ticker) if stock_info else ticker

                    # 1. 가격 데이터 수집 (스마트 수집 사용 - 중복 방지)
                    price_count = self.collector.collect_and_save_prices_smart(ticker, days=1)
                    total_price_records += price_count
                    logger.info(f"[{ticker}/{stock_name}] 가격 데이터: {price_count}건")

                    # 2. 매매동향 데이터 수집 (스마트 수집 사용 - 중복 방지)
                    trading_count = self.collector.collect_and_save_trading_flow_smart(ticker, days=1)
                    total_trading_records += trading_count
                    logger.info(f"[{ticker}/{stock_name}] 매매동향: {trading_count}건")

                    # 3. 뉴스 데이터 수집 (1일)
                    news_result = self.news_scraper.collect_and_save_news(ticker, days=1)
                    news_count = news_result.get('collected', 0)
                    total_news_records += news_count
                    logger.info(f"[{ticker}/{stock_name}] 뉴스: {news_count}건")

                    success_count += 1

                except Exception as e:
                    logger.error(f"[{ticker}] 데이터 수집 실패: {e}")
                    error_count += 1
                    continue

            end_time = datetime.now(KST)
            duration = (end_time - start_time).total_seconds()

            # 마지막 수집 시간 업데이트
            self.last_collection_time = end_time

            logger.info(
                f"[스케줄러-주기수집] 완료: "
                f"성공 {success_count}/{total_tickers}, 실패 {error_count}, "
                f"가격 {total_price_records}건, 매매동향 {total_trading_records}건, 뉴스 {total_news_records}건, "
                f"소요 시간 {duration:.2f}초"
            )

        except Exception as e:
            logger.error(f"[스케줄러-주기수집] 전체 실패: {e}", exc_info=True)
        finally:
            self.is_collecting = False

    def collect_daily_data(self):
        """
        일일 데이터 수집 작업 (기존 cron 작업)

        6개 종목의 당일 가격 데이터를 일괄 수집합니다.
        """
        start_time = datetime.now(KST)
        logger.info(f"[스케줄러-일일수집] 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # collect_all_tickers를 사용하여 일괄 수집
            result = self.collector.collect_all_tickers(days=1)

            logger.info(
                f"[스케줄러-일일수집] 완료: "
                f"성공 {result['success_count']}/{result['total_tickers']}, "
                f"실패 {result['fail_count']}, "
                f"총 {result['total_records']}개 레코드, "
                f"소요 시간 {result['duration_seconds']:.2f}초"
            )

            # 실패한 종목이 있으면 상세 로그
            if result['fail_count'] > 0:
                failed_tickers = [d for d in result['details'] if d['status'] == 'failed']
                for detail in failed_tickers:
                    logger.warning(
                        f"[스케줄러-일일수집] 실패: {detail['ticker']} - "
                        f"{detail.get('reason', 'Unknown error')}"
                    )

        except Exception as e:
            logger.error(f"[스케줄러-일일수집] 전체 실패: {e}", exc_info=True)
    
    def backfill_historical_data(self, days: int = 90):
        """
        히스토리 데이터 백필 작업
        
        Args:
            days: 백필할 일수 (기본 90일)
        """
        start_time = datetime.now(KST)
        logger.info(f"[스케줄러-백필] 시작: {days}일치 데이터, {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # backfill_all_tickers를 사용하여 일괄 백필
            result = self.collector.backfill_all_tickers(days=days)
            
            logger.info(
                f"[스케줄러-백필] 완료: "
                f"성공 {result['success_count']}/{result['total_tickers']}, "
                f"실패 {result['fail_count']}, "
                f"총 {result['total_records']}개 레코드, "
                f"소요 시간 {result['duration_seconds']:.2f}초"
            )
            
            # 실패한 종목이 있으면 상세 로그
            if result['fail_count'] > 0:
                failed_tickers = [d for d in result['details'] if d['status'] == 'failed']
                for detail in failed_tickers:
                    logger.warning(
                        f"[스케줄러-백필] 실패: {detail['ticker']} - "
                        f"{detail.get('reason', 'Unknown error')}"
                    )
                    
        except Exception as e:
            logger.error(f"[스케줄러-백필] 전체 실패: {e}", exc_info=True)
    
    def collect_ticker_catalog(self):
        """
        종목 목록 카탈로그 수집 작업
        
        매일 새벽에 전체 종목 목록(코스피, 코스닥, ETF)을 수집하여
        stock_catalog 테이블에 저장/업데이트합니다.
        - 신규 상장 종목 추가
        - 상장폐지 종목 표시 (is_active = 0)
        - 종목명 변경 반영
        """
        start_time = datetime.now(KST)
        logger.info(f"[스케줄러-카탈로그수집] 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            result = self.ticker_catalog_collector.collect_all_stocks()
            
            end_time = datetime.now(KST)
            self.last_catalog_collection_time = end_time
            
            logger.info(
                f"[스케줄러-카탈로그수집] 완료: "
                f"총 {result['total_collected']}개 종목 수집 "
                f"(코스피 {result['kospi_count']}개, 코스닥 {result['kosdaq_count']}개, ETF {result['etf_count']}개), "
                f"저장 {result['saved_count']}개, "
                f"소요 시간 {(end_time - start_time).total_seconds():.2f}초"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[스케줄러-카탈로그수집] 전체 실패: {e}", exc_info=True)
            raise
    
    def collect_catalog_data(self):
        """
        카탈로그 가격/수급 데이터 수집 작업

        ETF 종목의 가격, 거래량, 외국인/기관 순매수 데이터를 수집하여
        stock_catalog 테이블에 업데이트합니다.
        """
        start_time = datetime.now(KST)
        logger.info(f"[스케줄러-카탈로그데이터수집] 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            result = self.catalog_data_collector.collect_all()

            end_time = datetime.now(KST)
            self.last_catalog_data_collection_time = end_time

            logger.info(
                f"[스케줄러-카탈로그데이터수집] 완료: "
                f"가격 {result['price_count']}개, 수급 {result['supply_count']}개, "
                f"저장 {result['saved_count']}개, "
                f"소요 시간 {result['duration_seconds']}초"
            )

            return result

        except Exception as e:
            logger.error(f"[스케줄러-카탈로그데이터수집] 실패: {e}", exc_info=True)
            raise

    def start(self):
        """
        스케줄러 시작

        등록된 모든 작업을 활성화하고 스케줄러를 시작합니다.
        """
        if self.scheduler.running:
            logger.warning("스케줄러가 이미 실행 중입니다")
            return

        interval_minutes = Config.SCRAPING_INTERVAL_MINUTES

        # 주기적 데이터 수집 (설정된 간격마다 실행)
        periodic_job = self.scheduler.add_job(
            self.collect_periodic_data,
            trigger=IntervalTrigger(minutes=interval_minutes, timezone=KST),
            id='periodic_collection',
            name=f'주기적 데이터 수집 ({interval_minutes}분)',
            replace_existing=True
        )
        self._jobs['periodic_collection'] = periodic_job
        logger.info(f"주기적 수집 스케줄 등록: {interval_minutes}분마다 실행")

        # 일일 데이터 수집 스케줄 (평일 오후 3:30 KST)
        # 한국 주식시장은 평일 9:00-15:30에 운영되므로 장 마감 직후 수집
        daily_job = self.scheduler.add_job(
            self.collect_daily_data,
            trigger=CronTrigger(
                day_of_week='mon-fri',  # 월-금
                hour=15,
                minute=30,
                timezone=KST
            ),
            id='daily_collection',
            name='일일 데이터 수집',
            replace_existing=True
        )
        self._jobs['daily_collection'] = daily_job
        logger.info("일일 수집 스케줄 등록: 평일 15:30 KST")

        # 주간 히스토리 백필 (일요일 오전 2:00 KST)
        backfill_job = self.scheduler.add_job(
            self.backfill_historical_data,
            trigger=CronTrigger(
                day_of_week='sun',  # 일요일
                hour=2,
                minute=0,
                timezone=KST
            ),
            kwargs={'days': 90},
            id='weekly_backfill',
            name='주간 히스토리 백필',
            replace_existing=True
        )
        self._jobs['weekly_backfill'] = backfill_job
        logger.info("주간 백필 스케줄 등록: 일요일 02:00 KST (90일치)")

        # 종목 목록 카탈로그 수집 스케줄 (매일 새벽 3:00 KST)
        # 신규 상장 종목 추가 및 종목명 변경 반영을 위해 매일 실행
        catalog_job = self.scheduler.add_job(
            self.collect_ticker_catalog,
            trigger=CronTrigger(
                hour=3,
                minute=0,
                timezone=KST
            ),
            id='ticker_catalog_collection',
            name='종목 목록 카탈로그 수집',
            replace_existing=True
        )
        self._jobs['ticker_catalog_collection'] = catalog_job
        logger.info("종목 목록 카탈로그 수집 스케줄 등록: 매일 03:00 KST")

        # ETF 카탈로그 가격/수급 데이터 수집 스케줄 (평일 16:00 KST, 장 마감 30분 후)
        catalog_data_job = self.scheduler.add_job(
            self.collect_catalog_data,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour=16,
                minute=0,
                timezone=KST
            ),
            id='catalog_data_collection',
            name='ETF 카탈로그 가격/수급 수집',
            replace_existing=True
        )
        self._jobs['catalog_data_collection'] = catalog_data_job
        logger.info("ETF 카탈로그 가격/수급 수집 스케줄 등록: 평일 16:00 KST")

        # 스케줄러 시작
        self.scheduler.start()
        logger.info("스케줄러 시작 완료")

        # 즉시 첫 수집 실행
        logger.info("즉시 첫 주기적 수집 실행...")
        self.collect_periodic_data()
    
    def stop(self):
        """
        스케줄러 중지
        
        모든 작업을 중지하고 스케줄러를 종료합니다.
        """
        if not self.scheduler.running:
            logger.warning("스케줄러가 실행 중이 아닙니다")
            return
        
        self.scheduler.shutdown(wait=True)
        logger.info("스케줄러 종료 완료")
    
    def get_jobs(self):
        """
        등록된 작업 목록 조회

        Returns:
            list: 등록된 작업 정보 리스트
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs

    def is_running(self):
        """
        스케줄러 실행 상태 확인

        Returns:
            bool: 실행 중이면 True, 아니면 False
        """
        return self.scheduler.running

    def get_status(self):
        """
        스케줄러 상태 정보 조회

        Returns:
            dict: 스케줄러 상태 (실행 여부, 마지막 수집 시간, 다음 실행 시간 등)
        """
        next_job = None
        for job in self.scheduler.get_jobs():
            if job.id == 'periodic_collection' and job.next_run_time:
                next_job = job.next_run_time

        # 카탈로그 수집 다음 실행 시간 찾기
        catalog_next_job = None
        catalog_data_next_job = None
        for job in self.scheduler.get_jobs():
            if job.id == 'ticker_catalog_collection' and job.next_run_time:
                catalog_next_job = job.next_run_time
            if job.id == 'catalog_data_collection' and job.next_run_time:
                catalog_data_next_job = job.next_run_time

        return {
            "is_running": self.scheduler.running,
            "is_collecting": self.is_collecting,
            "last_collection_time": self.last_collection_time.isoformat() if self.last_collection_time else None,
            "last_catalog_collection_time": self.last_catalog_collection_time.isoformat() if self.last_catalog_collection_time else None,
            "last_catalog_data_collection_time": self.last_catalog_data_collection_time.isoformat() if self.last_catalog_data_collection_time else None,
            "interval_minutes": Config.SCRAPING_INTERVAL_MINUTES,
            "next_run_time": next_job.isoformat() if next_job else None,
            "next_catalog_collection_time": catalog_next_job.isoformat() if catalog_next_job else None,
            "next_catalog_data_collection_time": catalog_data_next_job.isoformat() if catalog_data_next_job else None,
        }


# 전역 스케줄러 인스턴스
_scheduler_instance = None


def get_scheduler() -> DataCollectionScheduler:
    """
    스케줄러 인스턴스 조회 (싱글톤 패턴)
    
    Returns:
        DataCollectionScheduler: 스케줄러 인스턴스
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = DataCollectionScheduler()
    return _scheduler_instance

