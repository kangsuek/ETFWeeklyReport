"""
배치 요약 서비스

대시보드 카드용으로 여러 종목의 최신 가격·차트 데이터·매매동향·뉴스를
배치 쿼리(N+1 방지)로 조합한다. (구 routers/etfs.py batch-summary 인라인 로직)
"""
import logging
from datetime import date, timedelta
from typing import List

from app.models import BatchSummaryResponse, ETFCardSummary, TradingFlow

logger = logging.getLogger(__name__)


def build_batch_summary(
    collector,
    tickers: List[str],
    price_days: int,
    news_limit: int,
) -> BatchSummaryResponse:
    """
    여러 종목의 요약 데이터 일괄 조회

    Args:
        collector: ETFDataCollector 인스턴스
        tickers: 종목 코드 리스트
        price_days: 가격 데이터 조회 일수
        news_limit: 종목별 뉴스 개수 제한

    Returns:
        BatchSummaryResponse — 데이터가 없는 종목도 빈 요약으로 포함 (에러 없음)
    """
    logger.debug(f"Fetching batch summary for {len(tickers)} tickers")

    result_data = {}

    end_date = date.today()
    start_date = end_date - timedelta(days=price_days)
    logger.debug(f"Date range: {start_date} to {end_date}")

    # 배치 쿼리로 모든 종목의 데이터를 한 번에 조회 (IN 절 활용)
    news_scraper = None
    try:
        prices_batch = collector.get_price_data_batch(tickers, start_date, end_date)
        logger.debug(f"Batch fetched prices for {len(prices_batch)} tickers")

        trading_flow_batch = collector.get_trading_flow_batch(tickers, start_date, end_date)
        logger.debug(f"Batch fetched trading flow for {len(trading_flow_batch)} tickers")

        # 뉴스는 ticker별로 조회 (데이터가 적어 IN 절 최적화 불필요)
        from app.services.news_scraper import NewsScraper
        news_scraper = NewsScraper()

    except Exception as e:
        logger.error(f"Error in batch queries: {e}", exc_info=True)
        # 배치 쿼리 실패 시 빈 결과로 처리
        prices_batch = {ticker: [] for ticker in tickers}
        trading_flow_batch = {ticker: [] for ticker in tickers}

    # 종목별로 데이터 조합
    for ticker in tickers:
        try:
            summary = ETFCardSummary(ticker=ticker)

            # 1. 가격 데이터 설정
            prices = prices_batch.get(ticker, [])
            if prices:
                summary.prices = prices
                summary.latest_price = prices[0] if prices else None

                # 주간 수익률 계산 (첫 가격과 마지막 가격 비교)
                if len(prices) >= 2:
                    first_price = prices[0].close_price
                    last_price = prices[-1].close_price
                    summary.weekly_return = ((first_price - last_price) / last_price) * 100
            else:
                logger.debug(f"[{ticker}] No price data found")

            # 2. 매매동향 설정
            trading_flow = trading_flow_batch.get(ticker, [])
            if trading_flow:
                summary.latest_trading_flow = TradingFlow(**trading_flow[0])

            # 3. 뉴스 조회 (ticker별)
            if news_scraper is not None:
                try:
                    news = news_scraper.get_news_for_ticker(ticker, start_date, end_date)
                    if news:
                        summary.latest_news = news[:news_limit]
                except Exception as e:
                    logger.warning(f"Error fetching news for {ticker}: {e}")

            result_data[ticker] = summary

        except Exception as e:
            logger.warning(f"Error processing summary for {ticker}: {e}")
            # 개별 종목 에러는 빈 객체로 처리
            result_data[ticker] = ETFCardSummary(ticker=ticker)

    logger.debug(f"Successfully fetched batch summary for {len(result_data)} tickers")
    return BatchSummaryResponse(data=result_data)
