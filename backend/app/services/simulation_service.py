"""
투자 시뮬레이션 서비스

일시 투자, 적립식(DCA), 포트폴리오 시뮬레이션
"""

import calendar
import logging
from datetime import date, timedelta
from typing import List, Optional

from app.models import (
    PriceData,
    LumpSumRequest, LumpSumResponse,
    DCARequest, DCAResponse, DCAMonthlyData,
    PortfolioSimulationRequest, PortfolioSimulationResponse,
)
from app.services.data_collector import ETFDataCollector
from app.utils.data_collection import auto_collect_if_needed

logger = logging.getLogger(__name__)


class SimulationService:
    def __init__(self, collector: ETFDataCollector):
        self.collector = collector

    def _ensure_prices(self, ticker: str, start_date: date, end_date: date) -> List[PriceData]:
        """가격 데이터 확보 (없으면 자동 수집). 날짜 오름차순 반환."""
        prices = auto_collect_if_needed(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            get_data_fn=self.collector.get_price_data,
            collect_fn=self.collector.collect_and_save_prices,
            data_type="price",
        )
        # get_price_data는 내림차순 → 오름차순으로 뒤집기
        return list(reversed(prices))

    @staticmethod
    def _find_nearest_trading_day(prices: List[PriceData], target: date) -> Optional[PriceData]:
        """target 이후 가장 가까운 거래일 가격 찾기 (오름차순 리스트 기준)."""
        for p in prices:
            if p.date >= target:
                return p
        return None

    # ───────────────── 일시 투자 ─────────────────

    def run_lump_sum(self, req: LumpSumRequest) -> LumpSumResponse:
        today = date.today()
        prices = self._ensure_prices(req.ticker, req.buy_date, today)

        if not prices:
            raise ValueError(f"가격 데이터가 없습니다: {req.ticker}")

        # 매수일 (또는 직후 거래일)
        buy_entry = self._find_nearest_trading_day(prices, req.buy_date)
        if not buy_entry:
            raise ValueError(f"매수일({req.buy_date}) 이후 거래 데이터가 없습니다")

        buy_price = buy_entry.close_price
        shares = int(req.amount // buy_price)
        remainder = req.amount - shares * buy_price

        if shares == 0:
            raise ValueError(f"투자금({req.amount:,.0f}원)으로 매수할 수 없습니다 (주가: {buy_price:,.0f}원)")

        # 시리즈 계산
        price_series = []
        max_gain = {"date": str(buy_entry.date), "price": buy_price, "return_pct": 0.0}
        max_loss = {"date": str(buy_entry.date), "price": buy_price, "return_pct": 0.0}

        for p in prices:
            if p.date < buy_entry.date:
                continue
            valuation = shares * p.close_price + remainder
            ret_pct = round((valuation - req.amount) / req.amount * 100, 2)

            price_series.append({
                "date": str(p.date),
                "close_price": p.close_price,
                "valuation": round(valuation, 0),
                "return_pct": ret_pct,
            })

            if ret_pct > max_gain["return_pct"]:
                max_gain = {"date": str(p.date), "price": p.close_price, "return_pct": ret_pct}
            if ret_pct < max_loss["return_pct"]:
                max_loss = {"date": str(p.date), "price": p.close_price, "return_pct": ret_pct}

        current = prices[-1]
        current_valuation = shares * current.close_price + remainder
        total_return_pct = round((current_valuation - req.amount) / req.amount * 100, 2)

        etf_info = self.collector.get_etf_info(req.ticker)
        name = etf_info.name if etf_info else req.ticker

        return LumpSumResponse(
            ticker=req.ticker,
            name=name,
            buy_date=buy_entry.date,
            buy_price=buy_price,
            current_date=current.date,
            current_price=current.close_price,
            shares=shares,
            remainder=round(remainder, 0),
            total_invested=req.amount,
            total_valuation=round(current_valuation, 0),
            total_return_pct=total_return_pct,
            max_gain=max_gain,
            max_loss=max_loss,
            price_series=price_series,
        )

    # ───────────────── 적립식 투자 ─────────────────

    def run_dca(self, req: DCARequest) -> DCAResponse:
        prices = self._ensure_prices(req.ticker, req.start_date, req.end_date)

        if not prices:
            raise ValueError(f"가격 데이터가 없습니다: {req.ticker}")

        monthly_data: List[DCAMonthlyData] = []
        cumulative_shares = 0
        cumulative_invested = 0.0
        total_cost = 0.0  # 총 매수 비용 (평균 매수가 계산용)
        cumulative_remainder = 0.0  # 누적 미투자 잔액

        # 매월 buy_day에 매수
        _, last_day = calendar.monthrange(req.start_date.year, req.start_date.month)
        target_day = min(req.buy_day, last_day)
        current = req.start_date.replace(day=target_day)
        if current < req.start_date:
            # buy_day가 start_date보다 앞이면 다음 달로
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        while current <= req.end_date:
            buy_entry = self._find_nearest_trading_day(prices, current)
            if not buy_entry:
                break

            buy_price = buy_entry.close_price
            shares_bought = int(req.monthly_amount // buy_price)

            if shares_bought > 0:
                cumulative_shares += shares_bought
                actual_cost = shares_bought * buy_price
                cumulative_invested += req.monthly_amount
                total_cost += actual_cost
                cumulative_remainder += (req.monthly_amount - actual_cost)

                valuation = cumulative_shares * buy_price + cumulative_remainder
                ret_pct = round((valuation - cumulative_invested) / cumulative_invested * 100, 2) if cumulative_invested > 0 else 0.0

                monthly_data.append(DCAMonthlyData(
                    date=buy_entry.date,
                    buy_price=buy_price,
                    shares_bought=shares_bought,
                    cumulative_shares=cumulative_shares,
                    cumulative_invested=cumulative_invested,
                    cumulative_valuation=round(valuation, 0),
                    return_pct=ret_pct,
                ))

            # 다음 달로 이동 (calendar.monthrange로 정확한 말일 계산)
            if current.month == 12:
                next_year, next_month = current.year + 1, 1
            else:
                next_year, next_month = current.year, current.month + 1
            _, last_day = calendar.monthrange(next_year, next_month)
            current = date(next_year, next_month, min(req.buy_day, last_day))

        if not monthly_data:
            raise ValueError("적립식 매수 가능한 거래일이 없습니다")

        # 최종 평가 (마지막 가격 기준)
        last_price = prices[-1].close_price
        total_valuation = cumulative_shares * last_price + cumulative_remainder
        total_return_pct = round((total_valuation - cumulative_invested) / cumulative_invested * 100, 2) if cumulative_invested > 0 else 0.0
        avg_buy_price = round(total_cost / cumulative_shares, 0) if cumulative_shares > 0 else 0.0

        etf_info = self.collector.get_etf_info(req.ticker)
        name = etf_info.name if etf_info else req.ticker

        return DCAResponse(
            ticker=req.ticker,
            name=name,
            total_invested=cumulative_invested,
            total_valuation=round(total_valuation, 0),
            total_return_pct=total_return_pct,
            avg_buy_price=avg_buy_price,
            total_shares=cumulative_shares,
            monthly_data=monthly_data,
        )

    # ───────────────── 포트폴리오 ─────────────────

    def run_portfolio(self, req: PortfolioSimulationRequest) -> PortfolioSimulationResponse:
        # 비중 합계 검증
        total_weight = sum(h.weight for h in req.holdings)
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"비중 합계가 1.0이 아닙니다 (현재: {total_weight:.2f})")

        # 중복 티커 검증
        tickers = [h.ticker for h in req.holdings]
        if len(tickers) != len(set(tickers)):
            raise ValueError("동일 종목이 중복 입력되었습니다")

        # 종목별 가격 데이터 확보
        ticker_prices = {}
        for h in req.holdings:
            prices = self._ensure_prices(h.ticker, req.start_date, req.end_date)
            if not prices:
                raise ValueError(f"가격 데이터가 없습니다: {h.ticker}")
            ticker_prices[h.ticker] = prices

        # 종목별 초기 매수
        holdings_result = []
        holdings_state = {}  # ticker -> { shares, buy_price, allocated }

        for h in req.holdings:
            allocated = req.amount * h.weight
            prices = ticker_prices[h.ticker]
            buy_entry = self._find_nearest_trading_day(prices, req.start_date)
            if not buy_entry:
                raise ValueError(f"시작일({req.start_date}) 이후 거래 데이터가 없습니다: {h.ticker}")

            buy_price = buy_entry.close_price
            shares = int(allocated // buy_price)
            remainder = allocated - shares * buy_price

            holdings_state[h.ticker] = {
                "shares": shares,
                "buy_price": buy_price,
                "allocated": allocated,
                "remainder": remainder,
                "weight": h.weight,
            }

        # 날짜별 포트폴리오 가치 계산
        # 모든 종목의 날짜 합집합 추출
        all_dates = set()
        for prices in ticker_prices.values():
            for p in prices:
                all_dates.add(p.date)
        sorted_dates = sorted(all_dates)

        # 종목별 날짜→가격 매핑 (forward-fill 적용)
        price_maps = {}
        for ticker, prices in ticker_prices.items():
            raw = {p.date: p.close_price for p in prices}
            filled = {}
            last_price = None
            for d in sorted_dates:
                if d in raw:
                    last_price = raw[d]
                if last_price is not None:
                    filled[d] = last_price
            price_maps[ticker] = filled

        daily_series = []
        for d in sorted_dates:
            total_val = 0.0
            all_have_data = True
            for ticker, state in holdings_state.items():
                if d in price_maps[ticker]:
                    total_val += state["shares"] * price_maps[ticker][d] + state["remainder"]
                else:
                    all_have_data = False
                    break

            if all_have_data and total_val > 0:
                ret_pct = round((total_val - req.amount) / req.amount * 100, 2)
                daily_series.append({
                    "date": str(d),
                    "valuation": round(total_val, 0),
                    "return_pct": ret_pct,
                })

        # 종목별 최종 결과
        for h in req.holdings:
            state = holdings_state[h.ticker]
            prices = ticker_prices[h.ticker]
            last_price = prices[-1].close_price
            current_val = state["shares"] * last_price + state["remainder"]
            ret_pct = round((current_val - state["allocated"]) / state["allocated"] * 100, 2) if state["allocated"] > 0 else 0.0

            etf_info = self.collector.get_etf_info(h.ticker)
            name = etf_info.name if etf_info else h.ticker

            holdings_result.append({
                "ticker": h.ticker,
                "name": name,
                "weight": h.weight,
                "allocated": state["allocated"],
                "buy_price": state["buy_price"],
                "shares": state["shares"],
                "current_price": last_price,
                "current_valuation": round(current_val, 0),
                "return_pct": ret_pct,
            })

        # 전체 포트폴리오 결과
        total_valuation = sum(r["current_valuation"] for r in holdings_result)
        total_return_pct = round((total_valuation - req.amount) / req.amount * 100, 2) if req.amount > 0 else 0.0

        return PortfolioSimulationResponse(
            total_invested=req.amount,
            total_valuation=round(total_valuation, 0),
            total_return_pct=total_return_pct,
            holdings_result=holdings_result,
            daily_series=daily_series,
        )
