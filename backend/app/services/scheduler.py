"""
스케줄러 서비스 모듈

APScheduler를 사용하여 정기적인 데이터 수집 작업을 스케줄링합니다.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from app.services.data_collector import ETFDataCollector

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
        self._jobs = {}
        logger.info("DataCollectionScheduler 초기화 완료")
    
    async def collect_daily_data(self):
        """
        일일 데이터 수집 작업
        
        6개 종목의 당일 가격 데이터를 수집합니다.
        """
        start_time = datetime.now(KST)
        logger.info(f"[일일 수집] 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 6개 종목 코드
        tickers = ['487240', '466920', '0020H0', '442320', '042660', '034020']
        
        success_count = 0
        fail_count = 0
        
        for ticker in tickers:
            try:
                # ETF/Stock 정보 확인
                etf_info = self.collector.get_etf_info(ticker)
                if not etf_info:
                    logger.warning(f"[일일 수집] 종목 정보 없음: {ticker}")
                    fail_count += 1
                    continue
                
                # 당일 데이터만 수집 (days=1)
                collected_count = await self.collector.collect_and_save_prices(ticker, days=1)
                
                if collected_count > 0:
                    logger.info(f"[일일 수집] {ticker} ({etf_info['name']}): {collected_count}개 수집 성공")
                    success_count += 1
                else:
                    logger.warning(f"[일일 수집] {ticker}: 수집 데이터 없음")
                    fail_count += 1
                    
            except Exception as e:
                logger.error(f"[일일 수집] {ticker} 실패: {e}")
                fail_count += 1
        
        end_time = datetime.now(KST)
        duration = (end_time - start_time).total_seconds()
        
        logger.info(
            f"[일일 수집] 완료: 성공 {success_count}개, 실패 {fail_count}개, "
            f"소요 시간 {duration:.2f}초"
        )
    
    async def backfill_historical_data(self, days: int = 90):
        """
        히스토리 데이터 백필 작업
        
        Args:
            days: 백필할 일수 (기본 90일)
        """
        start_time = datetime.now(KST)
        logger.info(f"[백필] 시작: {days}일치 데이터, {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        tickers = ['487240', '466920', '0020H0', '442320', '042660', '034020']
        
        total_collected = 0
        success_count = 0
        fail_count = 0
        
        for ticker in tickers:
            try:
                etf_info = self.collector.get_etf_info(ticker)
                if not etf_info:
                    logger.warning(f"[백필] 종목 정보 없음: {ticker}")
                    fail_count += 1
                    continue
                
                collected_count = await self.collector.collect_and_save_prices(ticker, days=days)
                
                if collected_count > 0:
                    logger.info(f"[백필] {ticker} ({etf_info['name']}): {collected_count}개 수집")
                    total_collected += collected_count
                    success_count += 1
                else:
                    logger.warning(f"[백필] {ticker}: 수집 데이터 없음")
                    fail_count += 1
                    
            except Exception as e:
                logger.error(f"[백필] {ticker} 실패: {e}")
                fail_count += 1
        
        end_time = datetime.now(KST)
        duration = (end_time - start_time).total_seconds()
        
        logger.info(
            f"[백필] 완료: 총 {total_collected}개 수집, 성공 {success_count}개, 실패 {fail_count}개, "
            f"소요 시간 {duration:.2f}초"
        )
    
    def start(self):
        """
        스케줄러 시작
        
        등록된 모든 작업을 활성화하고 스케줄러를 시작합니다.
        """
        if self.scheduler.running:
            logger.warning("스케줄러가 이미 실행 중입니다")
            return
        
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
        
        # 스케줄러 시작
        self.scheduler.start()
        logger.info("스케줄러 시작 완료")
    
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

