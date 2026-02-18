"""
Perplexity AI API service for stock/ETF analysis reports.

Uses the Perplexity sonar model with online search to generate
comprehensive investment analysis reports.
"""

import os
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

from app.database import get_db_connection, USE_POSTGRES

logger = logging.getLogger(__name__)

# Prompt template path (project root / prompt / perplexity.md)
PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "prompt" / "perplexity.md"

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar"
PERPLEXITY_TIMEOUT = 60
PERPLEXITY_TEMPERATURE = 0.2


class PerplexityService:
    """Perplexity AI investment analysis service."""

    def __init__(self):
        self._template: str | None = None

    def _fetch_db_context(self, ticker: str, name: str, days: int = 7) -> str:
        """
        DB에서 실제 데이터를 조회하여 구조화된 context를 생성합니다.

        Args:
            ticker: 종목 코드
            name: 종목명
            days: 조회할 거래일 수 (기본 7일)

        Returns:
            구조화된 DB 데이터 텍스트
        """
        param_placeholder = "%s" if USE_POSTGRES else "?"
        context_parts = []

        # 헤더
        context_parts.append("=" * 80)
        context_parts.append("⚠️  [중요] 아래는 실제 DB에서 조회한 데이터입니다.")
        context_parts.append("보고서 작성 시 **반드시 이 데이터를 우선적으로 사용**하고, 웹 검색은 보조적으로만 활용하세요.")
        context_parts.append("임의 추정치나 오래된 웹 데이터는 사용하지 마세요.")
        context_parts.append("=" * 80)
        context_parts.append("")
        context_parts.append(f"## 실제 DB 데이터: {name} ({ticker})")
        context_parts.append("")

        try:
            with get_db_connection() as conn_or_cursor:
                if USE_POSTGRES:
                    cursor = conn_or_cursor
                    conn = cursor.connection
                else:
                    conn = conn_or_cursor
                    cursor = conn.cursor()

                # 종목 타입 확인 (ETF vs STOCK)
                cursor.execute(f"""
                    SELECT type FROM etfs WHERE ticker = {param_placeholder}
                """, (ticker,))
                type_row = cursor.fetchone()
                ticker_type = ((type_row['type'] if USE_POSTGRES else type_row[0]) or 'ETF').upper() if type_row else 'ETF'
                is_etf = (ticker_type == 'ETF')

                # 1. 최근 N거래일 가격 데이터
                cursor.execute(f"""
                    SELECT date, open_price, high_price, low_price, close_price,
                           volume, daily_change_pct
                    FROM prices
                    WHERE ticker = {param_placeholder}
                    ORDER BY date DESC
                    LIMIT {param_placeholder}
                """, (ticker, days))

                prices = cursor.fetchall()
                if prices:
                    context_parts.append(f"### 1. 최근 {len(prices)}거래일 가격 데이터")
                    context_parts.append("")
                    context_parts.append("| 날짜 | 시가 | 고가 | 저가 | 종가 | 거래량 | 등락률(%) |")
                    context_parts.append("|------|------|------|------|------|--------|----------|")

                    for row in prices:
                        price_date = row['date'] if USE_POSTGRES else row[0]
                        open_p = row['open_price'] if USE_POSTGRES else row[1]
                        high_p = row['high_price'] if USE_POSTGRES else row[2]
                        low_p = row['low_price'] if USE_POSTGRES else row[3]
                        close_p = row['close_price'] if USE_POSTGRES else row[4]
                        volume = row['volume'] if USE_POSTGRES else row[5]
                        change_pct = row['daily_change_pct'] if USE_POSTGRES else row[6]

                        # 거래대금 계산 (억원)
                        trading_value = (close_p * volume / 100_000_000) if close_p and volume else 0

                        context_parts.append(
                            f"| {price_date} | "
                            f"{open_p:,.0f} | {high_p:,.0f} | {low_p:,.0f} | {close_p:,.0f} | "
                            f"{volume:,} | {change_pct:+.2f}% |"
                        )

                    # 주간 수익률 계산
                    if len(prices) >= 2:
                        first_close = prices[-1]['close_price'] if USE_POSTGRES else prices[-1][4]
                        last_close = prices[0]['close_price'] if USE_POSTGRES else prices[0][4]
                        if first_close and last_close:
                            weekly_return = ((last_close - first_close) / first_close) * 100
                            context_parts.append("")
                            context_parts.append(f"**주간 수익률**: {weekly_return:+.2f}%")

                    context_parts.append("")

                # 2. 매매동향 (투자자별 순매수) - 가격과 조인하여 금액 계산
                cursor.execute(f"""
                    SELECT tf.date, tf.individual_net, tf.institutional_net, tf.foreign_net, p.close_price
                    FROM trading_flow tf
                    LEFT JOIN prices p ON tf.ticker = p.ticker AND tf.date = p.date
                    WHERE tf.ticker = {param_placeholder}
                    ORDER BY tf.date DESC
                    LIMIT {param_placeholder}
                """, (ticker, days))

                flows = cursor.fetchall()
                if flows:
                    context_parts.append(f"### 2. 최근 {len(flows)}거래일 매매동향 (순매수)")
                    context_parts.append("")
                    context_parts.append("| 날짜 | 개인 (주) | 기관 (주) | 외국인 (주) | 개인 (억원) | 기관 (억원) | 외국인 (억원) |")
                    context_parts.append("|------|----------|----------|-----------|-----------|-----------|-------------|")

                    for row in flows:
                        flow_date = row['date'] if USE_POSTGRES else row[0]
                        individual_shares = (row['individual_net'] if USE_POSTGRES else row[1]) or 0
                        institutional_shares = (row['institutional_net'] if USE_POSTGRES else row[2]) or 0
                        foreign_shares = (row['foreign_net'] if USE_POSTGRES else row[3]) or 0
                        close_price = (row['close_price'] if USE_POSTGRES else row[4]) or 0

                        # 주수 → 금액(억원) 변환
                        if close_price > 0:
                            individual_krw = (individual_shares * close_price) / 100_000_000
                            institutional_krw = (institutional_shares * close_price) / 100_000_000
                            foreign_krw = (foreign_shares * close_price) / 100_000_000
                        else:
                            individual_krw = 0
                            institutional_krw = 0
                            foreign_krw = 0

                        context_parts.append(
                            f"| {flow_date} | "
                            f"{individual_shares:+,} | {institutional_shares:+,} | {foreign_shares:+,} | "
                            f"{individual_krw:+.1f} | {institutional_krw:+.1f} | {foreign_krw:+.1f} |"
                        )

                    context_parts.append("")

                # 3. 최근 뉴스 (최대 10개)
                cursor.execute(f"""
                    SELECT date, title, url, source, relevance_score
                    FROM news
                    WHERE ticker = {param_placeholder}
                    ORDER BY date DESC
                    LIMIT 10
                """, (ticker,))

                news_items = cursor.fetchall()
                if news_items:
                    context_parts.append(f"### 3. 최근 뉴스 ({len(news_items)}개)")
                    context_parts.append("")

                    for i, row in enumerate(news_items, 1):
                        news_date = row['date'] if USE_POSTGRES else row[0]
                        title = row['title'] if USE_POSTGRES else row[1]
                        url = row['url'] if USE_POSTGRES else row[2]
                        source = row['source'] if USE_POSTGRES else row[3]

                        context_parts.append(f"{i}. [{news_date}] {title}")
                        context_parts.append(f"   - 출처: {source}")
                        context_parts.append(f"   - URL: {url}")
                        context_parts.append("")

                # 4. 52주 최고/최저가 (최근 1년 데이터 기준)
                one_year_ago = (datetime.now() - timedelta(days=365)).date()
                cursor.execute(f"""
                    SELECT
                        MAX(high_price) as max_high,
                        MIN(low_price) as min_low
                    FROM prices
                    WHERE ticker = {param_placeholder}
                      AND date >= {param_placeholder}
                """, (ticker, one_year_ago))

                yearly_range = cursor.fetchone()
                if yearly_range:
                    max_high = yearly_range['max_high'] if USE_POSTGRES else yearly_range[0]
                    min_low = yearly_range['min_low'] if USE_POSTGRES else yearly_range[1]

                    if max_high and min_low and prices:
                        current_price = prices[0]['close_price'] if USE_POSTGRES else prices[0][4]
                        context_parts.append("### 4. 52주 최고/최저가 대비 현재가 위치")
                        context_parts.append("")
                        context_parts.append(f"- **52주 최고가**: {max_high:,.0f}원")
                        context_parts.append(f"- **52주 최저가**: {min_low:,.0f}원")
                        context_parts.append(f"- **현재가**: {current_price:,.0f}원")

                        # 현재가가 52주 범위에서 차지하는 위치 (%)
                        position = ((current_price - min_low) / (max_high - min_low)) * 100
                        context_parts.append(f"- **52주 범위 내 위치**: {position:.1f}%")
                        context_parts.append("")

                # 5. 기술적 분석 지표 (이동평균선, RSI, MACD)
                # 충분한 데이터 조회 (MA60 계산을 위해 최소 60일 + 여유분)
                cursor.execute(f"""
                    SELECT date, close_price, volume
                    FROM prices
                    WHERE ticker = {param_placeholder}
                    ORDER BY date DESC
                    LIMIT 100
                """, (ticker,))

                price_data = cursor.fetchall()
                if len(price_data) >= 20:  # 최소 20일 데이터 필요
                    context_parts.append("### 5. 기술적 분석 지표")
                    context_parts.append("")

                    # 종가 리스트 (최신순 → 오래된순으로 변환)
                    closes = [
                        (row['close_price'] if USE_POSTGRES else row[1])
                        for row in reversed(price_data)
                    ]

                    current_close = closes[-1]

                    # 이동평균선 계산
                    ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else None
                    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
                    ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else None

                    context_parts.append("**이동평균선 (MA)**:")
                    if ma5:
                        diff_ma5 = ((current_close - ma5) / ma5) * 100
                        context_parts.append(f"- MA5: {ma5:,.0f}원 (현재가 대비 {diff_ma5:+.2f}%)")
                    if ma20:
                        diff_ma20 = ((current_close - ma20) / ma20) * 100
                        context_parts.append(f"- MA20: {ma20:,.0f}원 (현재가 대비 {diff_ma20:+.2f}%)")
                    if ma60:
                        diff_ma60 = ((current_close - ma60) / ma60) * 100
                        context_parts.append(f"- MA60: {ma60:,.0f}원 (현재가 대비 {diff_ma60:+.2f}%)")

                    # 정배열/역배열 판단
                    if ma5 and ma20 and ma60:
                        if ma5 > ma20 > ma60:
                            context_parts.append(f"- **추세**: 정배열 (상승 추세)")
                        elif ma5 < ma20 < ma60:
                            context_parts.append(f"- **추세**: 역배열 (하락 추세)")
                        else:
                            context_parts.append(f"- **추세**: 혼조 (횡보)")

                    context_parts.append("")

                    # RSI(14) 계산
                    if len(closes) >= 15:
                        gains = []
                        losses = []
                        for i in range(1, len(closes)):
                            change = closes[i] - closes[i-1]
                            if change > 0:
                                gains.append(change)
                                losses.append(0)
                            else:
                                gains.append(0)
                                losses.append(abs(change))

                        # 최근 14일 평균
                        avg_gain = sum(gains[-14:]) / 14
                        avg_loss = sum(losses[-14:]) / 14

                        if avg_loss == 0:
                            rsi = 100
                        else:
                            rs = avg_gain / avg_loss
                            rsi = 100 - (100 / (1 + rs))

                        context_parts.append("**RSI(14)**:")
                        context_parts.append(f"- RSI: {rsi:.1f}")
                        if rsi >= 70:
                            context_parts.append(f"- **신호**: 과매수 구간 (≥70)")
                        elif rsi <= 30:
                            context_parts.append(f"- **신호**: 과매도 구간 (≤30)")
                        else:
                            context_parts.append(f"- **신호**: 중립")
                        context_parts.append("")

                    # MACD 계산 (12일, 26일 지수이동평균)
                    if len(closes) >= 26:
                        # EMA 계산 함수
                        def calculate_ema(data, period):
                            multiplier = 2 / (period + 1)
                            ema = [sum(data[:period]) / period]  # 첫 번째 EMA는 SMA
                            for price in data[period:]:
                                ema.append((price - ema[-1]) * multiplier + ema[-1])
                            return ema[-1]

                        ema12 = calculate_ema(closes, 12)
                        ema26 = calculate_ema(closes, 26)
                        macd_line = ema12 - ema26

                        # Signal line (MACD의 9일 EMA) - 간략화: 여기서는 MACD만 표시
                        context_parts.append("**MACD**:")
                        context_parts.append(f"- MACD Line: {macd_line:,.2f}")
                        context_parts.append(f"- EMA12: {ema12:,.0f}원")
                        context_parts.append(f"- EMA26: {ema26:,.0f}원")
                        if macd_line > 0:
                            context_parts.append(f"- **신호**: 상승 모멘텀 (MACD > 0)")
                        else:
                            context_parts.append(f"- **신호**: 하락 모멘텀 (MACD < 0)")
                        context_parts.append("")

                # 6. 동일 섹터 비교 ETF 수익률 (etfs 테이블에서 theme 기준)
                cursor.execute(f"""
                    SELECT theme FROM etfs WHERE ticker = {param_placeholder}
                """, (ticker,))
                theme_row = cursor.fetchone()

                if theme_row:
                    theme = theme_row['theme'] if USE_POSTGRES else theme_row[0]

                    if theme:
                        # 동일 theme를 가진 다른 종목들 찾기
                        cursor.execute(f"""
                            SELECT ticker, name, type
                            FROM etfs
                            WHERE theme = {param_placeholder} AND ticker != {param_placeholder}
                            LIMIT 5
                        """, (theme, ticker))

                        similar_etfs = cursor.fetchall()

                        if similar_etfs:
                            context_parts.append(f"### 6. 동일 섹터 비교 ({theme})")
                            context_parts.append("")
                            context_parts.append("| 종목명 (티커) | 현재가 | 주간 수익률 | 1개월 수익률 |")
                            context_parts.append("|--------------|--------|-----------|------------|")

                            for etf_row in similar_etfs:
                                comp_ticker = etf_row['ticker'] if USE_POSTGRES else etf_row[0]
                                comp_name = etf_row['name'] if USE_POSTGRES else etf_row[1]

                                # 최근 가격 조회
                                cursor.execute(f"""
                                    SELECT close_price FROM prices
                                    WHERE ticker = {param_placeholder}
                                    ORDER BY date DESC LIMIT 1
                                """, (comp_ticker,))
                                latest = cursor.fetchone()

                                if latest:
                                    latest_price = latest['close_price'] if USE_POSTGRES else latest[0]

                                    # 1주일 전 가격
                                    cursor.execute(f"""
                                        SELECT close_price FROM prices
                                        WHERE ticker = {param_placeholder}
                                        ORDER BY date DESC LIMIT 1 OFFSET 5
                                    """, (comp_ticker,))
                                    week_ago = cursor.fetchone()

                                    # 1개월 전 가격
                                    cursor.execute(f"""
                                        SELECT close_price FROM prices
                                        WHERE ticker = {param_placeholder}
                                        ORDER BY date DESC LIMIT 1 OFFSET 20
                                    """, (comp_ticker,))
                                    month_ago = cursor.fetchone()

                                    week_return = None
                                    month_return = None

                                    if week_ago:
                                        week_price = week_ago['close_price'] if USE_POSTGRES else week_ago[0]
                                        if week_price:
                                            week_return = ((latest_price - week_price) / week_price) * 100

                                    if month_ago:
                                        month_price = month_ago['close_price'] if USE_POSTGRES else month_ago[0]
                                        if month_price:
                                            month_return = ((latest_price - month_price) / month_price) * 100

                                    context_parts.append(
                                        f"| {comp_name} ({comp_ticker}) | "
                                        f"{latest_price:,.0f}원 | "
                                        f"{week_return:+.2f}% | " if week_return else "| - | "
                                        f"{month_return:+.2f}% |" if month_return else "- |"
                                    )

                            context_parts.append("")

                # 7. ETF 펀더멘털 데이터 (ETF 종목만)
                if is_etf:
                    context_parts.append("### 7. ETF 펀더멘털 데이터")
                    context_parts.append("")

                    # 7-1. NAV 추이 및 총보수 (최근 30일)
                    cursor.execute(f"""
                        SELECT date, nav, nav_change_pct, aum, tracking_error, expense_ratio
                        FROM etf_fundamentals
                        WHERE ticker = {param_placeholder}
                        ORDER BY date DESC
                        LIMIT 30
                    """, (ticker,))

                    fundamentals = cursor.fetchall()
                    if fundamentals:
                        # 총보수(expense_ratio)는 최신 행에서 추출
                        latest_expense = None
                        for _row in fundamentals:
                            _er = _row['expense_ratio'] if USE_POSTGRES else _row[5]
                            if _er is not None:
                                latest_expense = _er
                                break
                        if latest_expense is not None:
                            context_parts.append(f"- **총보수(연)**: {latest_expense:.2f}%")
                            context_parts.append("")

                        context_parts.append("**NAV 추이 (최근 10거래일)**:")
                        context_parts.append("")
                        context_parts.append("| 날짜 | NAV | NAV 변동(%) | 순자산(억원) | 추적오차(%) |")
                        context_parts.append("|------|-----|-----------|-----------|----------|")

                        for row in fundamentals[:10]:
                            fund_date = row['date'] if USE_POSTGRES else row[0]
                            nav = row['nav'] if USE_POSTGRES else row[1]
                            nav_change = row['nav_change_pct'] if USE_POSTGRES else row[2]
                            aum = row['aum'] if USE_POSTGRES else row[3]
                            tracking_error = row['tracking_error'] if USE_POSTGRES else row[4]

                            nav_str = f"{nav:,.0f}원" if nav else "-"
                            nav_change_str = f"{nav_change:+.2f}%" if nav_change else "-"
                            aum_str = f"{aum:,.0f}" if aum else "-"
                            tracking_error_str = f"{tracking_error:.2f}%" if tracking_error else "-"

                            context_parts.append(
                                f"| {fund_date} | "
                                f"{nav_str} | "
                                f"{nav_change_str} | "
                                f"{aum_str} | "
                                f"{tracking_error_str} |"
                            )

                        # 기간 NAV 변동률 요약
                        if len(fundamentals) >= 2:
                            first_nav = fundamentals[-1]['nav'] if USE_POSTGRES else fundamentals[-1][1]
                            latest_nav = fundamentals[0]['nav'] if USE_POSTGRES else fundamentals[0][1]
                            if first_nav and latest_nav:
                                nav_period_change = ((latest_nav - first_nav) / first_nav) * 100
                                context_parts.append("")
                                context_parts.append(f"- **기간 NAV 변동률** ({len(fundamentals)}거래일): {nav_period_change:+.2f}%")

                        context_parts.append("")

                    # 7-2. 최근 분배금 지급 내역
                    cursor.execute(f"""
                        SELECT record_date, payment_date, amount_per_share, distribution_type, yield_pct
                        FROM etf_distributions
                        WHERE ticker = {param_placeholder}
                        ORDER BY record_date DESC
                        LIMIT 5
                    """, (ticker,))

                    distributions = cursor.fetchall()
                    if distributions:
                        context_parts.append("**최근 분배금 지급 내역**:")
                        context_parts.append("")
                        context_parts.append("| 기준일 | 지급일 | 주당 분배금(원) | 유형 | 배당수익률(%) |")
                        context_parts.append("|--------|--------|---------------|------|-------------|")

                        for row in distributions:
                            rec_date = row['record_date'] if USE_POSTGRES else row[0]
                            pay_date = row['payment_date'] if USE_POSTGRES else row[1]
                            amount = row['amount_per_share'] if USE_POSTGRES else row[2]
                            dist_type = row['distribution_type'] if USE_POSTGRES else row[3]
                            yield_pct = row['yield_pct'] if USE_POSTGRES else row[4]

                            pay_date_str = pay_date if pay_date else "-"
                            amount_str = f"{amount:,.0f}" if amount else "-"
                            dist_type_str = dist_type if dist_type else "-"
                            yield_str = f"{yield_pct:.2f}%" if yield_pct else "-"

                            context_parts.append(
                                f"| {rec_date} | "
                                f"{pay_date_str} | "
                                f"{amount_str} | "
                                f"{dist_type_str} | "
                                f"{yield_str} |"
                            )

                        context_parts.append("")

                    # 7-3. 최근 리밸런싱 내역
                    cursor.execute(f"""
                        SELECT rebalance_date, action, stock_code, stock_name,
                               weight_before, weight_after, shares_change
                        FROM etf_rebalancing
                        WHERE ticker = {param_placeholder}
                        ORDER BY rebalance_date DESC
                        LIMIT 10
                    """, (ticker,))

                    rebalancing = cursor.fetchall()
                    if rebalancing:
                        context_parts.append("**최근 리밸런싱 내역**:")
                        context_parts.append("")
                        context_parts.append("| 일자 | 변경 | 종목코드 | 종목명 | 비중 변화 | 주식수 변화 |")
                        context_parts.append("|------|------|---------|--------|----------|-----------|")

                        for row in rebalancing:
                            rebal_date = row['rebalance_date'] if USE_POSTGRES else row[0]
                            action = row['action'] if USE_POSTGRES else row[1]
                            stock_code = row['stock_code'] if USE_POSTGRES else row[2]
                            stock_name = row['stock_name'] if USE_POSTGRES else row[3]
                            weight_before = row['weight_before'] if USE_POSTGRES else row[4]
                            weight_after = row['weight_after'] if USE_POSTGRES else row[5]
                            shares_change = row['shares_change'] if USE_POSTGRES else row[6]

                            action_kr = {'add': '편입', 'remove': '편출', 'adjust': '조정'}.get(action, action)

                            context_parts.append(
                                f"| {rebal_date} | "
                                f"{action_kr} | "
                                f"{stock_code} | "
                                f"{stock_name} | "
                                f"{weight_before:.1f}% → {weight_after:.1f}% | "
                                f"{shares_change:+,}주 |"
                            )

                        context_parts.append("")

                    # 7-4. 구성종목 상위 10개
                    cursor.execute(f"""
                        SELECT stock_code, stock_name, weight, shares, market_value, sector
                        FROM etf_holdings
                        WHERE ticker = {param_placeholder}
                          AND date = (
                              SELECT MAX(date) FROM etf_holdings WHERE ticker = {param_placeholder}
                          )
                        ORDER BY weight DESC
                        LIMIT 10
                    """, (ticker, ticker))

                    holdings = cursor.fetchall()
                    if holdings:
                        context_parts.append("**구성종목 상위 10개**:")
                        context_parts.append("")
                        context_parts.append("| 종목코드 | 종목명 | 편입비중(%) | 보유주식수 | 시가총액(억원) | 섹터 |")
                        context_parts.append("|---------|--------|-----------|----------|-------------|------|")

                        total_weight = 0
                        for row in holdings:
                            stock_code = row['stock_code'] if USE_POSTGRES else row[0]
                            stock_name = row['stock_name'] if USE_POSTGRES else row[1]
                            weight = row['weight'] if USE_POSTGRES else row[2]
                            shares = row['shares'] if USE_POSTGRES else row[3]
                            market_value = row['market_value'] if USE_POSTGRES else row[4]
                            sector = row['sector'] if USE_POSTGRES else row[5]

                            total_weight += weight or 0

                            weight_str = f"{weight:.2f}" if weight else "-"
                            shares_str = f"{shares:,}" if shares else "-"
                            market_value_str = f"{market_value:,.0f}" if market_value else "-"
                            sector_str = sector if sector else "-"

                            context_parts.append(
                                f"| {stock_code} | "
                                f"{stock_name} | "
                                f"{weight_str} | "
                                f"{shares_str} | "
                                f"{market_value_str} | "
                                f"{sector_str} |"
                            )

                        context_parts.append("")
                        context_parts.append(f"- **상위 10개 종목 비중 합계**: {total_weight:.2f}%")
                        context_parts.append("")

                # 8. 주식 펀더멘털 데이터 (STOCK 종목만)
                if not is_etf:
                    cursor.execute(f"""
                        SELECT * FROM stock_fundamentals
                        WHERE ticker = {param_placeholder}
                        ORDER BY date DESC
                        LIMIT 1
                    """, (ticker,))
                    stock_fund_row = cursor.fetchone()
                else:
                    stock_fund_row = None

                if stock_fund_row:
                    if USE_POSTGRES:
                        sf = dict(stock_fund_row)
                    else:
                        sf_cols = [d[0] for d in cursor.description]
                        sf = dict(zip(sf_cols, stock_fund_row))

                    context_parts.append("### 8. 주식 펀더멘털 데이터")
                    context_parts.append("")
                    context_parts.append(f"**기준일**: {sf.get('date', '-')}")
                    context_parts.append("")
                    context_parts.append("**밸류에이션 지표**:")
                    context_parts.append("")
                    context_parts.append("| 지표 | 값 |")
                    context_parts.append("|------|----|")

                    def _fmt(v, suffix=''):
                        return f"{v:,.2f}{suffix}" if v is not None else "-"

                    context_parts.append(f"| PER | {_fmt(sf.get('per'), '배')} |")
                    context_parts.append(f"| PBR | {_fmt(sf.get('pbr'), '배')} |")
                    context_parts.append(f"| ROE | {_fmt(sf.get('roe'), '%')} |")
                    context_parts.append(f"| EPS | {_fmt(sf.get('eps'), '원')} |")
                    context_parts.append(f"| BPS | {_fmt(sf.get('bps'), '원')} |")
                    context_parts.append(f"| 시가배당률 | {_fmt(sf.get('dividend_yield'), '%')} |")
                    context_parts.append(f"| 배당성향 | {_fmt(sf.get('payout_ratio'), '%')} |")
                    context_parts.append("")

                    context_parts.append("**실적 (억원 기준, 최근 연간)**:")
                    context_parts.append("")
                    context_parts.append("| 항목 | 값 |")
                    context_parts.append("|------|----|")
                    context_parts.append(f"| 매출액 | {_fmt(sf.get('revenue'), '억원')} |")
                    context_parts.append(f"| 영업이익 | {_fmt(sf.get('operating_profit'), '억원')} |")
                    context_parts.append(f"| 당기순이익 | {_fmt(sf.get('net_profit'), '억원')} |")
                    context_parts.append(f"| 영업이익률 | {_fmt(sf.get('operating_margin'), '%')} |")
                    context_parts.append(f"| 순이익률 | {_fmt(sf.get('net_margin'), '%')} |")
                    context_parts.append(f"| 부채비율 | {_fmt(sf.get('debt_ratio'), '%')} |")
                    context_parts.append(f"| 당좌비율 | {_fmt(sf.get('current_ratio'), '%')} |")
                    context_parts.append("")

                    # 8-2. 배당 이력
                    cursor.execute(f"""
                        SELECT record_date, amount_per_share, distribution_type, yield_pct
                        FROM stock_distributions
                        WHERE ticker = {param_placeholder}
                        ORDER BY record_date DESC
                        LIMIT 5
                    """, (ticker,))
                    dist_rows = cursor.fetchall()
                    if dist_rows:
                        context_parts.append("**최근 배당 이력**:")
                        context_parts.append("")
                        context_parts.append("| 기준일 | 주당배당금 | 유형 | 배당수익률 |")
                        context_parts.append("|--------|-----------|------|-----------|")
                        for dr in dist_rows:
                            if USE_POSTGRES:
                                d = dict(dr)
                                rec_date = d.get('record_date', '-')
                                amt = d.get('amount_per_share')
                                dist_type = d.get('distribution_type', '-')
                                yld = d.get('yield_pct')
                            else:
                                d_cols = [c[0] for c in cursor.description]
                                d = dict(zip(d_cols, dr))
                                rec_date = d.get('record_date', '-')
                                amt = d.get('amount_per_share')
                                dist_type = d.get('distribution_type', '-')
                                yld = d.get('yield_pct')
                            amt_str = f"{amt:,.0f}원" if amt else "-"
                            yld_str = f"{yld:.2f}%" if yld else "-"
                            context_parts.append(
                                f"| {rec_date} | {amt_str} | {dist_type} | {yld_str} |"
                            )
                        context_parts.append("")

        except Exception as e:
            logger.error(f"Error fetching DB context for {ticker}: {e}")
            context_parts.append(f"⚠️ DB 데이터 조회 중 오류 발생: {e}")
            context_parts.append("")

        return "\n".join(context_parts)

    def _get_api_key(self) -> str:
        key = os.getenv("PERPLEXITY_API_KEY", "")
        if not key or key.startswith("your_"):
            raise ValueError("PERPLEXITY_API_KEY가 설정되지 않았습니다. Settings 페이지에서 API 키를 입력해주세요.")
        return key

    def _load_template(self) -> str:
        if self._template is None:
            if not PROMPT_TEMPLATE_PATH.exists():
                raise FileNotFoundError(f"Prompt template not found: {PROMPT_TEMPLATE_PATH}")
            self._template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
        return self._template

    def _build_prompt(self, name: str, ticker: str, db_context: str = None) -> str:
        template = self._load_template()
        today_str = date.today().isoformat()  # e.g. "2026-02-14"

        prompt = (
            template
            .replace("{종목명}", name)
            .replace("{티커코드}", ticker)
            .replace("YYYY-MM-DD", today_str)
        )

        # DB 데이터 context가 있으면 프롬프트 앞에 추가
        if db_context:
            prompt = f"""{db_context}

---

{prompt}"""

        return prompt

    def get_prompt(self, ticker: str, name: str, use_db_data: bool = True) -> str:
        """
        Return the generated prompt without calling Perplexity API.

        Args:
            ticker: Stock/ETF ticker code
            name: Stock/ETF name
            use_db_data: DB 데이터를 context로 포함할지 여부 (기본: True)

        Returns:
            Generated prompt with optional DB context
        """
        db_context = None
        if use_db_data:
            logger.info(f"Fetching DB data for prompt generation: {ticker}")
            db_context = self._fetch_db_context(ticker, name)

        return self._build_prompt(name, ticker, db_context)

    def get_multi_prompt(self, stocks: list[dict], use_db_data: bool = True) -> str:
        """
        Return the generated multi-stock prompt without calling Perplexity API.

        Args:
            stocks: List of dicts with 'ticker' and 'name' keys
            use_db_data: DB 데이터를 context로 포함할지 여부 (기본: True)

        Returns:
            Generated multi-stock prompt with optional DB context
        """
        base_prompt = self._build_multi_prompt(stocks)

        if use_db_data:
            logger.info(f"Fetching DB data for multi-stock prompt: {len(stocks)} stocks")
            # 각 종목의 DB context를 수집
            db_contexts = []
            for stock in stocks:
                ticker = stock['ticker']
                name = stock['name']
                context = self._fetch_db_context(ticker, name)
                db_contexts.append(context)

            # 모든 context를 결합
            combined_context = "\n\n".join(db_contexts)
            return f"""{combined_context}

---

{base_prompt}"""

        return base_prompt

    def _build_multi_prompt(self, stocks: list[dict]) -> str:
        """Build a combined analysis prompt for multiple stocks."""
        today_str = date.today().isoformat()
        names = ", ".join(f"{s['name']}({s['ticker']})" for s in stocks)
        stock_list = "\n".join(f"- **{s['name']}** ({s['ticker']})" for s in stocks)

        return f"""당신은 한국 주식·ETF를 전문적으로 분석하는 **리서치 애널리스트**입니다.
아래 종목들에 대한 **통합 비교 투자분석 보고서**를 작성하세요.

### 분석 대상 종목
{stock_list}

### 공통 작성 규칙
- 모든 수치는 **최신 실제 데이터**만 사용하고, 임의 추정치는 사용하지 마세요.
- 리포트 작성 기준일은 **{today_str}**로 설정하고, "최근 7거래일"은 이 기준일을 포함해 직전 7개 거래일로 정의하세요.
- 데이터 출처(예: KRX, 네이버금융, 인베스팅닷컴, 운용사 웹사이트 등)를 문장 중간에서 간단히 언급하세요.
- 한국 투자자를 대상으로, 한국어(존댓말)로 작성하세요.
- 분량은 최소 5,000단어 수준으로 **상세하게** 작성하세요.

---

## 1. 종목 개요 비교

각 종목({names})의 기본 정보(테마, 운용사, 총보수, 상장일 등)와 최근 주가·수익률을 비교표로 정리하세요.

---

## 2. 주간 시장 데이터 비교 (최근 7거래일)

각 종목의 최근 7거래일 종가, 등락률, 거래량을 종목별로 나란히 비교하는 표를 작성하고 핵심 요약을 제공하세요.

---

## 3. 기술적 분석 비교

각 종목의 이동평균선(5/20/60일), RSI(14), MACD, 볼린저밴드 상태를 비교표로 정리하고, 종목 간 기술적 강약을 분석하세요.

---

## 4. 시장 환경 및 섹터 비교

각 종목이 속한 섹터의 글로벌·국내 핵심 이슈를 정리하고, 섹터 간 상대적 모멘텀을 비교하세요.

---

## 5. 수급 분석 비교

각 종목의 최근 7거래일 개인/기관/외국인 순매수 동향을 비교표로 정리하고, 수급 관점의 유리한 종목을 평가하세요.

---

## 6. 펀더멘털 비교

각 종목의 NAV, 괴리율, 총보수, 수익률(1개월/3개월/YTD) 등을 비교표로 정리하세요.

---

## 7. 상관관계 및 분산 효과

종목 간 가격 상관관계를 정성적으로 평가하고, 포트폴리오 분산 효과가 있는지 분석하세요.

---

## 8. 종합 비교 매력도 순위

모든 분석을 종합하여 종목별 투자 매력도를 순위로 정리하세요. 각 종목의 강점·약점을 1~2줄로 요약하세요.

| 순위 | 종목 | 투자 매력도 | 핵심 강점 | 주요 리스크 |
|------|------|------------|----------|------------|

---

## 9. 투자자 유형별 추천

- **공격적 투자자**: 위 종목 중 비중 확대 추천 종목과 근거
- **보수적 투자자**: 안정적 선택지와 분할 매수 전략
- **포트폴리오 조합 제안**: 위 종목들의 최적 비중 배분 가이드

---

## 10. 종합 의견 및 액션 플랜

- 각 종목에 대한 단기(1주)/중기(1~3개월) 전망
- 종목 간 상대적 우선순위와 교체 매매 전략
- 구체적인 분할 매수/매도 기준

---

위 템플릿 전체를 반영하여, 실제 투자 의사결정에 바로 활용 가능한 **고품질 통합 비교 리포트**를 작성하세요."""

    def analyze(self, ticker: str, name: str, use_db_data: bool = True) -> dict:
        """
        Call Perplexity API to generate an investment analysis report.

        Args:
            ticker: Stock/ETF ticker code
            name: Stock/ETF name
            use_db_data: DB 데이터를 context로 사용할지 여부 (기본: True)

        Returns:
            dict with 'content' (Markdown report) and 'citations' (list of source URLs)

        Raises:
            ValueError: If API key is not configured
            RuntimeError: If API call fails
        """
        api_key = self._get_api_key()

        # DB 데이터를 context로 추가
        db_context = None
        if use_db_data:
            logger.info(f"Fetching DB data for {ticker} to enhance prompt with RAG context")
            db_context = self._fetch_db_context(ticker, name)
            logger.info(f"DB context length: {len(db_context)} characters")

        prompt = self._build_prompt(name, ticker, db_context)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": PERPLEXITY_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": PERPLEXITY_TEMPERATURE,
        }

        logger.info(f"Calling Perplexity API for {name}({ticker})")

        try:
            response = requests.post(
                PERPLEXITY_API_URL,
                json=payload,
                headers=headers,
                timeout=PERPLEXITY_TIMEOUT,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error(f"Perplexity API timeout for {ticker}")
            raise RuntimeError("Perplexity API 요청 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            logger.error(f"Perplexity API HTTP error {status} for {ticker}: {e}")
            if status == 401:
                raise RuntimeError("Perplexity API 키가 유효하지 않습니다. Settings에서 확인해주세요.")
            elif status == 429:
                raise RuntimeError("Perplexity API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
            raise RuntimeError(f"Perplexity API 호출 실패 (HTTP {status})")
        except requests.exceptions.RequestException as e:
            logger.error(f"Perplexity API request error for {ticker}: {e}")
            raise RuntimeError("Perplexity API 연결에 실패했습니다.")

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected Perplexity API response format: {e}")
            raise RuntimeError("Perplexity API 응답 형식이 올바르지 않습니다.")

        # Extract citations from Perplexity response
        citations = data.get("citations", [])

        # Replace [1], [2], ... with markdown links to citations
        if citations:
            import re
            def replace_citation(match):
                idx = int(match.group(1))
                if 1 <= idx <= len(citations):
                    url = citations[idx - 1]
                    return f"[[{idx}]]({url})"
                return match.group(0)
            content = re.sub(r'\[(\d+)\]', replace_citation, content)

        logger.info(f"Perplexity analysis completed for {name}({ticker}), length={len(content)}, citations={len(citations)}")
        return {"content": content, "citations": citations, "prompt": prompt}

    def analyze_multi(self, stocks: list[dict]) -> dict:
        """
        Call Perplexity API to generate a combined investment analysis report for multiple stocks.

        Args:
            stocks: List of dicts with 'ticker' and 'name' keys

        Returns:
            dict with 'content' (Markdown report) and 'citations' (list of source URLs)
        """
        api_key = self._get_api_key()

        # 각 종목의 DB 컨텍스트 수집 (RAG)
        logger.info(f"Fetching DB data for multi-stock analysis: {len(stocks)} stocks")
        db_contexts = []
        for stock in stocks:
            ctx = self._fetch_db_context(stock['ticker'], stock['name'])
            db_contexts.append(ctx)
        combined_context = "\n\n".join(db_contexts)

        base_prompt = self._build_multi_prompt(stocks)
        prompt = f"{combined_context}\n\n---\n\n{base_prompt}"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": PERPLEXITY_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": PERPLEXITY_TEMPERATURE,
        }

        names = ", ".join(f"{s['name']}({s['ticker']})" for s in stocks)
        logger.info(f"Calling Perplexity API for multi-stock analysis: {names}")

        try:
            response = requests.post(
                PERPLEXITY_API_URL,
                json=payload,
                headers=headers,
                timeout=PERPLEXITY_TIMEOUT * 2,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error(f"Perplexity API timeout for multi-stock: {names}")
            raise RuntimeError("Perplexity API 요청 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            logger.error(f"Perplexity API HTTP error {status} for multi-stock: {e}")
            if status == 401:
                raise RuntimeError("Perplexity API 키가 유효하지 않습니다. Settings에서 확인해주세요.")
            elif status == 429:
                raise RuntimeError("Perplexity API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
            raise RuntimeError(f"Perplexity API 호출 실패 (HTTP {status})")
        except requests.exceptions.RequestException as e:
            logger.error(f"Perplexity API request error for multi-stock: {e}")
            raise RuntimeError("Perplexity API 연결에 실패했습니다.")

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected Perplexity API response format: {e}")
            raise RuntimeError("Perplexity API 응답 형식이 올바르지 않습니다.")

        citations = data.get("citations", [])

        if citations:
            import re
            def replace_citation(match):
                idx = int(match.group(1))
                if 1 <= idx <= len(citations):
                    url = citations[idx - 1]
                    return f"[[{idx}]]({url})"
                return match.group(0)
            content = re.sub(r'\[(\d+)\]', replace_citation, content)

        logger.info(f"Perplexity multi-stock analysis completed for {names}, length={len(content)}, citations={len(citations)}")
        return {"content": content, "citations": citations, "prompt": prompt}
