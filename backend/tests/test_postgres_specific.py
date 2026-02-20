"""
PostgreSQL 전용 통합 테스트

실행 방법:
    just pg-up                  # 테스트용 PostgreSQL 컨테이너 시작
    just test-postgres          # 테스트 실행
    just pg-down                # 컨테이너 종료

또는 직접 실행:
    cd backend && \\
    DATABASE_URL=postgresql://etf_user:etf_pass@localhost:5433/etf_test \\
    uv run pytest tests/test_postgres_specific.py -v

사전 조건:
    docker-compose up -d postgres-test
"""
import pytest
import psycopg2

from app.database import USE_POSTGRES, init_db, run_migrations, get_db_connection

pytestmark = pytest.mark.skipif(
    not USE_POSTGRES,
    reason="PostgreSQL 전용 테스트 (DATABASE_URL=postgresql://... 필요, 'just pg-up' 먼저 실행)"
)

# 테스트용 임시 티커 (실제 종목 코드와 겹치지 않는 값)
_TEST_TICKER = "T99999"


@pytest.fixture(autouse=True)
def setup_pg_db():
    """각 테스트마다 DB 스키마 초기화 및 마이그레이션"""
    init_db()
    run_migrations()
    yield
    # 테스트 종목 정리
    _cleanup_test_ticker()


def _get_column_type(table: str, column: str) -> str | None:
    """information_schema에서 컬럼 타입 조회"""
    with get_db_connection() as cursor:
        cursor.execute(
            """
            SELECT data_type FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
            """,
            (table, column),
        )
        row = cursor.fetchone()
        return row["data_type"].upper() if row else None


def _cleanup_test_ticker():
    """테스트에서 삽입한 _TEST_TICKER 관련 데이터 일괄 삭제"""
    fk_tables = [
        "alert_history",  # alert_rules 먼저
        "alert_rules",
        "collection_status",
        "intraday_prices",
        "etf_fundamentals",
        "etf_rebalancing",
        "etf_distributions",
        "etf_holdings",
        "stock_fundamentals",
        "stock_distributions",
        "prices",
        "news",
        "trading_flow",
        "stock_catalog",
    ]
    with get_db_connection() as cursor:
        conn = cursor.connection
        for table in fk_tables:
            try:
                cursor.execute(f"DELETE FROM {table} WHERE ticker = %s", (_TEST_TICKER,))
            except Exception:
                conn.rollback()
        try:
            cursor.execute("DELETE FROM etfs WHERE ticker = %s", (_TEST_TICKER,))
            conn.commit()
        except Exception:
            conn.rollback()


def _insert_test_etf():
    """테스트용 기본 종목을 etfs 테이블에 삽입"""
    with get_db_connection() as cursor:
        conn = cursor.connection
        cursor.execute(
            """
            INSERT INTO etfs (ticker, name, type)
            VALUES (%s, %s, %s)
            ON CONFLICT (ticker) DO NOTHING
            """,
            (_TEST_TICKER, "테스트종목", "ETF"),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# 1. 스키마 검증
# ---------------------------------------------------------------------------

class TestInitDB:
    """init_db()가 PostgreSQL에서 모든 테이블을 정상 생성하는지 검증"""

    EXPECTED_TABLES = [
        "etfs",
        "prices",
        "trading_flow",
        "news",
        "collection_status",
        "intraday_prices",
        "alert_rules",
        "alert_history",
        "etf_fundamentals",
        "etf_rebalancing",
        "etf_distributions",
        "etf_holdings",
        "stock_fundamentals",
        "stock_distributions",
        "stock_catalog",
    ]

    def test_all_expected_tables_created(self):
        """init_db() 후 모든 필수 테이블이 존재해야 한다"""
        with get_db_connection() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            existing = {row["table_name"] for row in cursor.fetchall()}

        missing = [t for t in self.EXPECTED_TABLES if t not in existing]
        assert not missing, f"누락된 테이블: {missing}"

    def test_stock_catalog_has_week_base_columns(self):
        """stock_catalog에 week_base_price, week_base_date 컬럼이 존재해야 한다"""
        assert _get_column_type("stock_catalog", "week_base_price") is not None, \
            "week_base_price 컬럼 없음"
        assert _get_column_type("stock_catalog", "week_base_date") is not None, \
            "week_base_date 컬럼 없음"


# ---------------------------------------------------------------------------
# 2. BIGINT 마이그레이션 검증
# ---------------------------------------------------------------------------

class TestBigintMigration:
    """run_migrations()가 foreign_net/institutional_net을 BIGINT로 변환하는지 검증"""

    def test_foreign_net_is_bigint(self):
        """stock_catalog.foreign_net 컬럼 타입이 BIGINT이어야 한다"""
        col_type = _get_column_type("stock_catalog", "foreign_net")
        assert col_type == "BIGINT", \
            f"foreign_net 타입={col_type!r}, BIGINT 필요 (run_migrations() 실패 가능)"

    def test_institutional_net_is_bigint(self):
        """stock_catalog.institutional_net 컬럼 타입이 BIGINT이어야 한다"""
        col_type = _get_column_type("stock_catalog", "institutional_net")
        assert col_type == "BIGINT", \
            f"institutional_net 타입={col_type!r}, BIGINT 필요 (run_migrations() 실패 가능)"

    def test_large_foreign_net_does_not_overflow(self):
        """INTEGER 범위(±2.1B)를 초과하는 값을 저장해도 오류가 없어야 한다"""
        LARGE_VALUE = 9_999_999_999  # ~99.9억: INTEGER max(2.1억) 초과

        _insert_test_etf()

        with get_db_connection() as cursor:
            conn = cursor.connection
            cursor.execute(
                """
                INSERT INTO stock_catalog (ticker, name, type, market, is_active,
                    foreign_net, institutional_net)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker) DO UPDATE SET
                    foreign_net = EXCLUDED.foreign_net,
                    institutional_net = EXCLUDED.institutional_net
                """,
                (_TEST_TICKER, "테스트종목", "ETF", "ETF", True, LARGE_VALUE, -LARGE_VALUE),
            )
            conn.commit()

        with get_db_connection() as cursor:
            cursor.execute(
                "SELECT foreign_net, institutional_net FROM stock_catalog WHERE ticker = %s",
                (_TEST_TICKER,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row["foreign_net"] == LARGE_VALUE
        assert row["institutional_net"] == -LARGE_VALUE

    def test_value_exceeding_integer_range_was_previously_failing(self):
        """
        BIGINT 이전(INTEGER)에 발생하던 오류를 시뮬레이션.
        stock_catalog.foreign_net이 BIGINT인 지금은 오류 없이 저장되어야 한다.
        """
        # INTEGER max = 2,147,483,647 / BIGINT max = 9,223,372,036,854,775,807
        OVERFLOW_VALUE = 3_000_000_000  # 30억: INTEGER 오버플로우, BIGINT 정상

        _insert_test_etf()

        with get_db_connection() as cursor:
            conn = cursor.connection
            # 이 INSERT가 예외 없이 완료되면 BIGINT가 정상 작동하는 것
            cursor.execute(
                """
                INSERT INTO stock_catalog (ticker, name, type, market, is_active, foreign_net)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker) DO UPDATE SET foreign_net = EXCLUDED.foreign_net
                """,
                (_TEST_TICKER, "테스트종목", "ETF", "ETF", True, OVERFLOW_VALUE),
            )
            conn.commit()


# ---------------------------------------------------------------------------
# 3. FK 제약조건 삭제 순서 검증
# ---------------------------------------------------------------------------

class TestFKConstraints:
    """etfs 삭제 시 FK 참조 테이블 선삭제 여부를 검증"""

    def setup_method(self):
        _insert_test_etf()

    def test_direct_delete_etfs_with_collection_status_raises_fk(self):
        """collection_status가 있는 상태에서 etfs 직접 삭제 시 FK 오류가 발생해야 한다"""
        with get_db_connection() as cursor:
            conn = cursor.connection
            cursor.execute(
                "INSERT INTO collection_status (ticker) VALUES (%s) ON CONFLICT DO NOTHING",
                (_TEST_TICKER,),
            )
            conn.commit()

        with get_db_connection() as cursor:
            conn = cursor.connection
            with pytest.raises(psycopg2.errors.ForeignKeyViolation):
                cursor.execute("DELETE FROM etfs WHERE ticker = %s", (_TEST_TICKER,))
                conn.commit()
            conn.rollback()

    def test_correct_delete_order_succeeds(self):
        """FK 테이블 선삭제 → etfs 삭제 순서로 오류 없이 삭제되어야 한다"""
        with get_db_connection() as cursor:
            conn = cursor.connection
            cursor.execute(
                "INSERT INTO collection_status (ticker) VALUES (%s) ON CONFLICT DO NOTHING",
                (_TEST_TICKER,),
            )
            cursor.execute(
                "INSERT INTO etf_fundamentals (ticker, date) VALUES (%s, CURRENT_DATE) ON CONFLICT DO NOTHING",
                (_TEST_TICKER,),
            )
            conn.commit()

        with get_db_connection() as cursor:
            conn = cursor.connection
            cursor.execute("DELETE FROM collection_status WHERE ticker = %s", (_TEST_TICKER,))
            cursor.execute("DELETE FROM etf_fundamentals WHERE ticker = %s", (_TEST_TICKER,))
            cursor.execute("DELETE FROM etfs WHERE ticker = %s", (_TEST_TICKER,))
            conn.commit()

        with get_db_connection() as cursor:
            cursor.execute("SELECT COUNT(*) AS cnt FROM etfs WHERE ticker = %s", (_TEST_TICKER,))
            assert cursor.fetchone()["cnt"] == 0

    def test_direct_delete_etfs_with_etf_fundamentals_raises_fk(self):
        """etf_fundamentals가 있는 상태에서 etfs 직접 삭제 시 FK 오류가 발생해야 한다"""
        with get_db_connection() as cursor:
            conn = cursor.connection
            cursor.execute(
                "INSERT INTO etf_fundamentals (ticker, date) VALUES (%s, CURRENT_DATE) ON CONFLICT DO NOTHING",
                (_TEST_TICKER,),
            )
            conn.commit()

        with get_db_connection() as cursor:
            conn = cursor.connection
            with pytest.raises(psycopg2.errors.ForeignKeyViolation):
                cursor.execute("DELETE FROM etfs WHERE ticker = %s", (_TEST_TICKER,))
                conn.commit()
            conn.rollback()


# ---------------------------------------------------------------------------
# 4. run_migrations() 멱등성 검증
# ---------------------------------------------------------------------------

class TestRunMigrationsIdempotent:
    """run_migrations()를 여러 번 실행해도 오류 없이 같은 결과를 내야 한다"""

    def test_run_migrations_twice_no_error(self):
        """run_migrations() 두 번 호출 시 오류 없어야 한다"""
        run_migrations()  # setup_pg_db fixture에서 이미 1회 실행됨, 추가로 1회 더
        # 오류 없이 완료되면 통과

    def test_column_types_unchanged_after_second_migration(self):
        """두 번째 run_migrations() 후에도 BIGINT 타입 유지"""
        run_migrations()
        assert _get_column_type("stock_catalog", "foreign_net") == "BIGINT"
        assert _get_column_type("stock_catalog", "institutional_net") == "BIGINT"
