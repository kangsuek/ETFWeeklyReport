"""
데이터 정합성 검증 스크립트

데이터베이스의 데이터 품질을 검증하고 리포트를 생성합니다.
- 중복 데이터 체크
- NULL 값 통계
- 날짜 연속성 확인
- 가격 이상치 탐지
- 종목별 수집 현황
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict
import sys

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db_connection
from app.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataQualityValidator:
    """데이터 품질 검증 클래스"""

    def __init__(self):
        self.conn = get_db_connection()
        self.issues = defaultdict(list)
        self.stats = {}

    def check_duplicate_prices(self) -> Dict[str, int]:
        """
        가격 데이터 중복 체크

        Returns:
            종목별 중복 건수
        """
        logger.info("가격 데이터 중복 체크 시작...")

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT ticker, date, COUNT(*) as count
            FROM prices
            GROUP BY ticker, date
            HAVING count > 1
        """)

        duplicates = {}
        for row in cursor.fetchall():
            ticker = row['ticker']
            duplicates[ticker] = duplicates.get(ticker, 0) + row['count'] - 1
            self.issues['duplicates'].append({
                'table': 'prices',
                'ticker': ticker,
                'date': row['date'],
                'count': row['count']
            })

        logger.info(f"중복 데이터: {len(self.issues['duplicates'])}건")
        return duplicates

    def check_null_values(self) -> Dict[str, Dict[str, int]]:
        """
        NULL 값 통계

        Returns:
            테이블별, 컬럼별 NULL 건수
        """
        logger.info("NULL 값 통계 수집 시작...")

        null_stats = {}
        cursor = self.conn.cursor()

        # prices 테이블 NULL 체크
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN open_price IS NULL THEN 1 ELSE 0 END) as null_open,
                SUM(CASE WHEN high_price IS NULL THEN 1 ELSE 0 END) as null_high,
                SUM(CASE WHEN low_price IS NULL THEN 1 ELSE 0 END) as null_low,
                SUM(CASE WHEN close_price IS NULL THEN 1 ELSE 0 END) as null_close,
                SUM(CASE WHEN volume IS NULL THEN 1 ELSE 0 END) as null_volume,
                SUM(CASE WHEN daily_change_pct IS NULL THEN 1 ELSE 0 END) as null_change_pct
            FROM prices
        """)

        row = cursor.fetchone()
        total = row['total']

        if total > 0:
            null_stats['prices'] = {
                'total_records': total,
                'open_price': row['null_open'],
                'high_price': row['null_high'],
                'low_price': row['null_low'],
                'close_price': row['null_close'],
                'volume': row['null_volume'],
                'daily_change_pct': row['null_change_pct']
            }

            for col, count in null_stats['prices'].items():
                if col != 'total_records' and count > 0:
                    self.issues['null_values'].append({
                        'table': 'prices',
                        'column': col,
                        'count': count,
                        'percentage': round(count / total * 100, 2)
                    })

        # trading_flow 테이블 NULL 체크
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN individual_net IS NULL THEN 1 ELSE 0 END) as null_individual,
                SUM(CASE WHEN institutional_net IS NULL THEN 1 ELSE 0 END) as null_institutional,
                SUM(CASE WHEN foreign_net IS NULL THEN 1 ELSE 0 END) as null_foreign
            FROM trading_flow
        """)

        row = cursor.fetchone()
        total = row['total']

        if total > 0:
            null_stats['trading_flow'] = {
                'total_records': total,
                'individual_net': row['null_individual'],
                'institutional_net': row['null_institutional'],
                'foreign_net': row['null_foreign']
            }

        logger.info(f"NULL 값 이슈: {len(self.issues['null_values'])}건")
        return null_stats

    def check_date_continuity(self) -> Dict[str, List[str]]:
        """
        날짜 연속성 확인 (주말 제외)

        Returns:
            종목별 누락된 날짜 목록
        """
        logger.info("날짜 연속성 확인 시작...")

        missing_dates = {}
        cursor = self.conn.cursor()

        # 각 종목별로 날짜 연속성 확인
        stock_config = Config.get_stock_config()

        for ticker in stock_config.keys():
            cursor.execute("""
                SELECT date
                FROM prices
                WHERE ticker = ?
                ORDER BY date
            """, (ticker,))

            dates = [datetime.strptime(row['date'], '%Y-%m-%d').date()
                    for row in cursor.fetchall()]

            if len(dates) < 2:
                continue

            # 첫 날짜부터 마지막 날짜까지의 모든 평일 계산
            start_date = dates[0]
            end_date = dates[-1]

            expected_dates = []
            current = start_date
            while current <= end_date:
                # 주말(토요일=5, 일요일=6) 제외
                if current.weekday() < 5:
                    expected_dates.append(current)
                current += timedelta(days=1)

            # 실제 날짜와 비교
            actual_dates_set = set(dates)
            missing = [d for d in expected_dates if d not in actual_dates_set]

            if missing:
                missing_dates[ticker] = [d.strftime('%Y-%m-%d') for d in missing]
                self.issues['missing_dates'].append({
                    'ticker': ticker,
                    'count': len(missing),
                    'dates': missing_dates[ticker][:5]  # 처음 5개만 표시
                })

        logger.info(f"날짜 누락 이슈: {len(self.issues['missing_dates'])}개 종목")
        return missing_dates

    def check_price_anomalies(self) -> Dict[str, List[Dict]]:
        """
        가격 이상치 탐지

        Returns:
            종목별 이상치 목록
        """
        logger.info("가격 이상치 탐지 시작...")

        anomalies = {}
        cursor = self.conn.cursor()

        stock_config = Config.get_stock_config()

        for ticker in stock_config.keys():
            ticker_anomalies = []

            # 1. 가격 관계 위반 체크 (high < low, close > high, close < low 등)
            cursor.execute("""
                SELECT date, open_price, high_price, low_price, close_price
                FROM prices
                WHERE ticker = ?
                AND (
                    (high_price IS NOT NULL AND low_price IS NOT NULL AND high_price < low_price)
                    OR (high_price IS NOT NULL AND close_price IS NOT NULL AND close_price > high_price)
                    OR (low_price IS NOT NULL AND close_price IS NOT NULL AND close_price < low_price)
                    OR (high_price IS NOT NULL AND open_price IS NOT NULL AND open_price > high_price)
                    OR (low_price IS NOT NULL AND open_price IS NOT NULL AND open_price < low_price)
                )
            """, (ticker,))

            for row in cursor.fetchall():
                ticker_anomalies.append({
                    'date': row['date'],
                    'type': 'price_relationship_violation',
                    'open': row['open_price'],
                    'high': row['high_price'],
                    'low': row['low_price'],
                    'close': row['close_price']
                })

            # 2. 급격한 가격 변동 체크 (전일 대비 ±50% 이상)
            cursor.execute("""
                SELECT date, close_price, daily_change_pct
                FROM prices
                WHERE ticker = ?
                AND ABS(daily_change_pct) > 50.0
                ORDER BY date
            """, (ticker,))

            for row in cursor.fetchall():
                ticker_anomalies.append({
                    'date': row['date'],
                    'type': 'extreme_price_change',
                    'close_price': row['close_price'],
                    'change_pct': row['daily_change_pct']
                })

            if ticker_anomalies:
                anomalies[ticker] = ticker_anomalies
                self.issues['anomalies'].append({
                    'ticker': ticker,
                    'count': len(ticker_anomalies),
                    'examples': ticker_anomalies[:3]
                })

        logger.info(f"가격 이상치: {sum(len(v) for v in anomalies.values())}건")
        return anomalies

    def get_collection_status(self) -> Dict[str, Dict]:
        """
        종목별 수집 현황

        Returns:
            종목별 통계 정보
        """
        logger.info("종목별 수집 현황 조회...")

        status = {}
        cursor = self.conn.cursor()

        stock_config = Config.get_stock_config()

        for ticker, info in stock_config.items():
            # 가격 데이터 통계
            cursor.execute("""
                SELECT
                    COUNT(*) as count,
                    MIN(date) as first_date,
                    MAX(date) as last_date
                FROM prices
                WHERE ticker = ?
            """, (ticker,))

            price_row = cursor.fetchone()

            # 매매 동향 데이터 통계
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM trading_flow
                WHERE ticker = ?
            """, (ticker,))

            trading_row = cursor.fetchone()

            # 뉴스 데이터 통계
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM news
                WHERE ticker = ?
            """, (ticker,))

            news_row = cursor.fetchone()

            status[ticker] = {
                'name': info['name'],
                'type': info['type'],
                'prices': {
                    'count': price_row['count'],
                    'first_date': price_row['first_date'],
                    'last_date': price_row['last_date']
                },
                'trading_flow': {
                    'count': trading_row['count']
                },
                'news': {
                    'count': news_row['count']
                }
            }

        return status

    def calculate_completeness_score(self, status: Dict) -> Dict[str, float]:
        """
        데이터 완전성 점수 계산 (0-100)

        Args:
            status: 종목별 수집 현황

        Returns:
            종목별 완전성 점수
        """
        logger.info("데이터 완전성 점수 계산...")

        scores = {}

        for ticker, data in status.items():
            score = 0.0

            # 가격 데이터 (50점)
            if data['prices']['count'] > 0:
                score += 50.0

            # 매매 동향 데이터 (25점)
            if data['trading_flow']['count'] > 0:
                score += 25.0

            # 뉴스 데이터 (25점)
            if data['news']['count'] > 0:
                score += 25.0

            scores[ticker] = score

        return scores

    def generate_report(self) -> str:
        """
        데이터 품질 리포트 생성

        Returns:
            마크다운 형식의 리포트
        """
        logger.info("데이터 품질 리포트 생성 시작...")

        # 모든 검증 실행
        duplicates = self.check_duplicate_prices()
        null_stats = self.check_null_values()
        missing_dates = self.check_date_continuity()
        anomalies = self.check_price_anomalies()
        status = self.get_collection_status()
        scores = self.calculate_completeness_score(status)

        # 리포트 생성
        report = []
        report.append("# 데이터 품질 검증 리포트")
        report.append(f"\n**생성 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 1. 종합 요약
        report.append("## 📊 종합 요약\n")
        total_issues = sum(len(v) for v in self.issues.values())
        report.append(f"- **총 이슈 건수**: {total_issues}건")
        report.append(f"  - 중복 데이터: {len(self.issues['duplicates'])}건")
        report.append(f"  - NULL 값: {len(self.issues['null_values'])}건")
        report.append(f"  - 날짜 누락: {len(self.issues['missing_dates'])}개 종목")
        report.append(f"  - 가격 이상치: {sum(len(v) for v in anomalies.values())}건")

        # 2. 종목별 수집 현황
        report.append("\n## 📈 종목별 수집 현황\n")
        report.append("| 종목코드 | 종목명 | 타입 | 가격 데이터 | 매매 동향 | 뉴스 | 완전성 점수 |")
        report.append("|---------|-------|------|-----------|----------|------|------------|")

        for ticker, data in status.items():
            report.append(
                f"| {ticker} | {data['name']} | {data['type']} | "
                f"{data['prices']['count']}건 | "
                f"{data['trading_flow']['count']}건 | "
                f"{data['news']['count']}건 | "
                f"{scores[ticker]:.0f}점 |"
            )

        # 3. 데이터 수집 기간
        report.append("\n## 📅 데이터 수집 기간\n")
        report.append("| 종목코드 | 최초 수집일 | 최근 수집일 | 수집 일수 |")
        report.append("|---------|-----------|-----------|---------|")

        for ticker, data in status.items():
            if data['prices']['count'] > 0:
                report.append(
                    f"| {ticker} | {data['prices']['first_date']} | "
                    f"{data['prices']['last_date']} | {data['prices']['count']}일 |"
                )

        # 4. NULL 값 통계
        if null_stats:
            report.append("\n## ⚠️ NULL 값 통계\n")
            for table, stats in null_stats.items():
                total = stats.get('total_records', 0)
                if total > 0:
                    report.append(f"\n### {table} 테이블\n")
                    report.append("| 컬럼 | NULL 건수 | 비율 |")
                    report.append("|------|----------|------|")

                    for col, count in stats.items():
                        if col != 'total_records' and count > 0:
                            pct = round(count / total * 100, 2)
                            report.append(f"| {col} | {count}건 | {pct}% |")

        # 5. 날짜 누락 이슈
        if self.issues['missing_dates']:
            report.append("\n## 📆 날짜 누락 이슈\n")
            for issue in self.issues['missing_dates']:
                report.append(f"\n### {issue['ticker']} ({issue['count']}일 누락)")
                if issue['dates']:
                    report.append(f"- 예시: {', '.join(issue['dates'][:5])}")
                    if issue['count'] > 5:
                        report.append(f"  - (외 {issue['count'] - 5}일 더 누락)")

        # 6. 가격 이상치
        if self.issues['anomalies']:
            report.append("\n## 🚨 가격 이상치\n")
            for issue in self.issues['anomalies']:
                report.append(f"\n### {issue['ticker']} ({issue['count']}건)")
                for example in issue['examples']:
                    report.append(f"- {example['date']}: {example['type']}")

        # 7. 권장 사항
        report.append("\n## 💡 권장 사항\n")
        if total_issues == 0:
            report.append("✅ 데이터 품질이 우수합니다. 이슈가 발견되지 않았습니다.")
        else:
            if self.issues['duplicates']:
                report.append("- 중복 데이터 정리 필요")
            if self.issues['missing_dates']:
                report.append("- 누락된 날짜의 데이터 재수집 권장")
            if self.issues['anomalies']:
                report.append("- 가격 이상치 확인 및 데이터 재검증 필요")

        return "\n".join(report)

    def close(self):
        """리소스 정리"""
        self.conn.close()


def main():
    """메인 함수"""
    print("=" * 80)
    print("데이터 품질 검증 시작")
    print("=" * 80)

    validator = DataQualityValidator()

    try:
        # 리포트 생성
        report = validator.generate_report()

        # 콘솔 출력
        print("\n" + report)

        # 파일 저장
        report_path = Path(__file__).parent.parent / "data" / "data_quality_report.md"
        report_path.write_text(report, encoding='utf-8')

        print(f"\n리포트 저장: {report_path}")
        print("=" * 80)

    finally:
        validator.close()


if __name__ == "__main__":
    main()
