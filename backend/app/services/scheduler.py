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
    
    def collect_daily_data(self):
        """
        일일 데이터 수집 작업
        
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

