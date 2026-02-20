"""
Scanner API 라우터

ETF 조건 검색, 테마 탐색, 추천 프리셋 제공
"""
import logging
from fastapi import APIRouter, Query, BackgroundTasks
from typing import Optional, List
from app.database import get_db_connection, get_cursor, USE_POSTGRES
from app.models import ScreeningItem, ScreeningResponse, ThemeGroup, RecommendationPreset
from app.utils.cache import get_cache, make_cache_key

logger = logging.getLogger(__name__)

router = APIRouter()

SCANNER_CACHE_TTL = 60  # 60초


def _row_to_screening_item(row, registered_tickers: set) -> ScreeningItem:
    """DB row를 ScreeningItem으로 변환"""
    return ScreeningItem(
        ticker=row['ticker'],
        name=row['name'],
        type=row['type'],
        market=row.get('market'),
        sector=row.get('sector'),
        close_price=row.get('close_price'),
        daily_change_pct=row.get('daily_change_pct'),
        volume=row.get('volume'),
        weekly_return=row.get('weekly_return'),
        foreign_net=row.get('foreign_net'),
        institutional_net=row.get('institutional_net'),
        catalog_updated_at=str(row['catalog_updated_at']) if row.get('catalog_updated_at') else None,
        is_registered=row['ticker'] in registered_tickers
    )


def _get_registered_tickers(existing_cursor=None) -> set:
    """etfs 테이블에 등록된 종목 티커 set 반환"""
    if existing_cursor:
        existing_cursor.execute("SELECT ticker FROM etfs")
        return {row['ticker'] if USE_POSTGRES else row[0] for row in existing_cursor.fetchall()}
    with get_db_connection() as conn_or_cursor:
        cursor = get_cursor(conn_or_cursor)
        cursor.execute("SELECT ticker FROM etfs")
        return {row['ticker'] if USE_POSTGRES else row[0] for row in cursor.fetchall()}


@router.get("", response_model=ScreeningResponse)
async def search_scanner(
    q: Optional[str] = Query(None, description="종목명/코드 검색"),
    type: str = Query("ETF", description="ETF / STOCK / ALL"),
    market: Optional[str] = Query(None, description="시장 필터: ETF / KOSPI / KOSDAQ"),
    sector: Optional[str] = Query(None, description="섹터 필터"),
    min_weekly_return: Optional[float] = Query(None, description="최소 주간수익률"),
    max_weekly_return: Optional[float] = Query(None, description="최대 주간수익률"),
    foreign_net_positive: Optional[bool] = Query(None, description="외국인 순매수만"),
    institutional_net_positive: Optional[bool] = Query(None, description="기관 순매수만"),
    sort_by: str = Query("weekly_return", description="정렬 기준"),
    sort_dir: str = Query("desc", description="정렬 방향"),
    page: int = Query(1, ge=1, description="페이지"),
    page_size: int = Query(20, ge=1, le=50, description="페이지 크기"),
):
    """조건 기반 종목 검색"""
    cache = get_cache()
    cache_key = make_cache_key(
        "scanner", q=q, type=type, market=market, sector=sector,
        min_wr=min_weekly_return, max_wr=max_weekly_return,
        fnp=foreign_net_positive, inp=institutional_net_positive,
        sort_by=sort_by, sort_dir=sort_dir, page=page, page_size=page_size
    )
    cached = cache.get(cache_key)
    if cached:
        return cached

    p = "%s" if USE_POSTGRES else "?"
    is_active_where = "sc.is_active = true" if USE_POSTGRES else "sc.is_active = 1"
    where_clauses = [is_active_where]
    params = []

    # market 파라미터가 있으면 market 기준 필터 (ETF/KOSPI/KOSDAQ)
    # market=ALL이면 전체 조회 (type 필터도 적용하지 않음)
    if market and market != "ALL":
        where_clauses.append(f"sc.market = {p}")
        params.append(market)
    elif not market and type != "ALL":
        where_clauses.append(f"sc.type = {p}")
        params.append(type)

    if q:
        where_clauses.append(f"(sc.ticker LIKE {p} OR sc.name LIKE {p})")
        params.extend([f"%{q}%", f"%{q}%"])

    if sector:
        where_clauses.append(f"sc.sector = {p}")
        params.append(sector)

    if min_weekly_return is not None:
        where_clauses.append(f"sc.weekly_return >= {p}")
        params.append(min_weekly_return)

    if max_weekly_return is not None:
        where_clauses.append(f"sc.weekly_return <= {p}")
        params.append(max_weekly_return)

    if foreign_net_positive:
        where_clauses.append("sc.foreign_net > 0")

    if institutional_net_positive:
        where_clauses.append("sc.institutional_net > 0")

    # catalog_updated_at이 있는 항목만 (데이터가 수집된 종목)
    where_clauses.append("sc.catalog_updated_at IS NOT NULL")

    where_sql = " AND ".join(where_clauses)

    # 정렬 컬럼 화이트리스트 (키: 파라미터명, 값: 실제 컬럼명)
    ALLOWED_SORT_COLUMNS = {
        "weekly_return": "sc.weekly_return",
        "daily_change_pct": "sc.daily_change_pct",
        "volume": "sc.volume",
        "close_price": "sc.close_price",
        "foreign_net": "sc.foreign_net",
        "institutional_net": "sc.institutional_net",
        "name": "sc.name",
    }
    sort_column = ALLOWED_SORT_COLUMNS.get(sort_by, "sc.weekly_return")
    sort_dir_sql = "ASC" if sort_dir == "asc" else "DESC"

    with get_db_connection() as conn_or_cursor:
        cursor = get_cursor(conn_or_cursor)
        registered_tickers = _get_registered_tickers(cursor)

        # 전체 건수
        cursor.execute(f"SELECT COUNT(*) as cnt FROM stock_catalog sc WHERE {where_sql}", params)
        row = cursor.fetchone()
        total = row['cnt'] if USE_POSTGRES else row[0]

        # 데이터 조회
        offset = (page - 1) * page_size
        query_params = params + [page_size, offset]

        if USE_POSTGRES:
            order_clause = f"{sort_column} {sort_dir_sql} NULLS LAST"
        else:
            # SQLite NULL 처리
            order_clause = f"CASE WHEN {sort_column} IS NULL THEN 1 ELSE 0 END, {sort_column} {sort_dir_sql}"

        cursor.execute(f"""
            SELECT sc.ticker, sc.name, sc.type, sc.market, sc.sector,
                   sc.close_price, sc.daily_change_pct, sc.volume,
                   sc.weekly_return, sc.foreign_net, sc.institutional_net,
                   sc.catalog_updated_at
            FROM stock_catalog sc
            WHERE {where_sql}
            ORDER BY {order_clause}
            LIMIT {p} OFFSET {p}
        """, query_params)

        rows = cursor.fetchall()

    items = [_row_to_screening_item(dict(row), registered_tickers) for row in rows]

    result = ScreeningResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )
    cache.set(cache_key, result, ttl_seconds=SCANNER_CACHE_TTL)
    return result


@router.get("/themes", response_model=List[ThemeGroup])
async def get_themes():
    """섹터/테마별 그룹 조회"""
    cache = get_cache()
    cache_key = "scanner:themes"
    cached = cache.get(cache_key)
    if cached:
        return cached

    p = "%s" if USE_POSTGRES else "?"

    with get_db_connection() as conn_or_cursor:
        cursor = get_cursor(conn_or_cursor)
        registered_tickers = _get_registered_tickers(cursor)

        # 섹터별 집계 (PostgreSQL: is_active boolean, SQLite: integer 1/0)
        is_active_cmp = "is_active = true" if USE_POSTGRES else "is_active = 1"
        cursor.execute(f"""
            SELECT sector, COUNT(*) as cnt,
                   AVG(weekly_return) as avg_wr
            FROM stock_catalog
            WHERE {is_active_cmp}
              AND sector IS NOT NULL
              AND sector != ''
              AND catalog_updated_at IS NOT NULL
            GROUP BY sector
            ORDER BY avg_wr DESC
        """)

        sectors = [dict(row) for row in cursor.fetchall()]

        # 전체 섹터의 top 3 종목을 한 번의 쿼리로 조회 (윈도우 함수)
        cursor.execute(f"""
            SELECT * FROM (
                SELECT ticker, name, type, market, sector,
                       close_price, daily_change_pct, volume,
                       weekly_return, foreign_net, institutional_net,
                       catalog_updated_at,
                       ROW_NUMBER() OVER (
                           PARTITION BY sector
                           ORDER BY CASE WHEN weekly_return IS NULL THEN 1 ELSE 0 END,
                                    weekly_return DESC
                       ) as rn
                FROM stock_catalog
                WHERE {is_active_cmp}
                  AND sector IS NOT NULL
                  AND sector != ''
                  AND catalog_updated_at IS NOT NULL
            ) ranked
            WHERE rn <= 3
        """)

        top_rows = cursor.fetchall()
        # 섹터별로 그룹핑
        top_by_sector = {}
        for r in top_rows:
            row = dict(r)
            sector_name = row['sector']
            if sector_name not in top_by_sector:
                top_by_sector[sector_name] = []
            top_by_sector[sector_name].append(
                _row_to_screening_item(row, registered_tickers)
            )

        themes = []
        for s in sectors:
            sector_name = s['sector']
            avg_wr = s.get('avg_wr')

            themes.append(ThemeGroup(
                sector=sector_name,
                count=s['cnt'],
                avg_weekly_return=round(avg_wr, 2) if avg_wr is not None else None,
                top_performers=top_by_sector.get(sector_name, [])
            ))

    cache.set(cache_key, themes, ttl_seconds=SCANNER_CACHE_TTL)
    return themes


@router.get("/recommendations", response_model=List[RecommendationPreset])
async def get_recommendations(
    limit: int = Query(5, ge=1, le=10, description="각 프리셋별 종목 수")
):
    """추천 프리셋 (주간 상위, 외국인 매수 등)"""
    cache = get_cache()
    cache_key = f"scanner:recommendations:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    p = "%s" if USE_POSTGRES else "?"

    presets_config = [
        {
            "preset_id": "weekly_top_return",
            "title": "주간 수익률 상위",
            "description": "최근 1주간 수익률이 높은 ETF",
            "order_by": "weekly_return DESC",
            "extra_where": "weekly_return IS NOT NULL"
        },
        {
            "preset_id": "foreign_buying",
            "title": "외국인 순매수 상위",
            "description": "외국인 매수세가 강한 ETF",
            "order_by": "foreign_net DESC",
            "extra_where": "foreign_net > 0"
        },
        {
            "preset_id": "institutional_buying",
            "title": "기관 순매수 상위",
            "description": "기관 매수세가 강한 ETF",
            "order_by": "institutional_net DESC",
            "extra_where": "institutional_net > 0"
        },
        {
            "preset_id": "high_volume",
            "title": "거래량 상위",
            "description": "거래가 활발한 ETF",
            "order_by": "volume DESC",
            "extra_where": "volume IS NOT NULL AND volume > 0"
        },
        {
            "preset_id": "weekly_worst_return",
            "title": "주간 하락 상위 (역발상)",
            "description": "최근 1주간 하락폭이 큰 ETF (역발상 투자 참고)",
            "order_by": "weekly_return ASC",
            "extra_where": "weekly_return IS NOT NULL"
        },
    ]

    results = []

    with get_db_connection() as conn_or_cursor:
        cursor = get_cursor(conn_or_cursor)
        registered_tickers = _get_registered_tickers(cursor)

        is_active_cmp = "is_active = true" if USE_POSTGRES else "is_active = 1"
        for preset in presets_config:
            # NULLS LAST 처리
            if USE_POSTGRES:
                order_clause = f"{preset['order_by']} NULLS LAST"
            else:
                order_clause = preset['order_by']

            cursor.execute(f"""
                SELECT ticker, name, type, market, sector,
                       close_price, daily_change_pct, volume,
                       weekly_return, foreign_net, institutional_net,
                       catalog_updated_at
                FROM stock_catalog
                WHERE {is_active_cmp}
                  AND type = 'ETF'
                  AND catalog_updated_at IS NOT NULL
                  AND {preset['extra_where']}
                ORDER BY {order_clause}
                LIMIT {p}
            """, (limit,))

            rows = cursor.fetchall()

            if not rows:
                continue

            items = [_row_to_screening_item(dict(r), registered_tickers) for r in rows]

            results.append(RecommendationPreset(
                preset_id=preset['preset_id'],
                title=preset['title'],
                description=preset['description'],
                items=items
            ))

    cache.set(cache_key, results, ttl_seconds=SCANNER_CACHE_TTL)
    return results


@router.get("/collect-progress")
async def get_collect_progress():
    """카탈로그 데이터 수집 진행률 조회"""
    from app.services.progress import get_progress
    progress = get_progress("catalog-data")
    return progress or {"status": "idle"}


@router.post("/collect-data")
async def trigger_collect_data(background_tasks: BackgroundTasks):
    """카탈로그 데이터 수동 수집 트리거"""
    from app.services.catalog_data_collector import CatalogDataCollector
    from app.services.progress import clear_progress, get_progress

    # 이미 수집 중인지 확인
    current = get_progress("catalog-data")
    if current and current.get("status") == "in_progress":
        return {"message": "이미 데이터 수집이 진행 중입니다", "status": "already_running"}

    # 이전 취소 플래그 초기화
    clear_progress("catalog-data")

    collector = CatalogDataCollector()

    background_tasks.add_task(collector.collect_all)

    return {"message": "카탈로그 데이터 수집이 시작되었습니다", "status": "started"}


@router.post("/cancel-collect")
async def cancel_collect_data():
    """진행 중인 카탈로그 데이터 수집 중지"""
    from app.services.progress import request_cancel, get_progress

    progress = get_progress("catalog-data")
    if not progress or progress.get("status") != "in_progress":
        return {"message": "진행 중인 수집이 없습니다", "status": "idle"}

    request_cancel("catalog-data")
    return {"message": "수집 중지 요청됨", "status": "cancelling"}
