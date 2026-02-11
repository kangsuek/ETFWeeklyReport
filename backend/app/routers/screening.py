"""
스크리닝 API 라우터

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

SCREENING_CACHE_TTL = 60  # 60초


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


def _get_registered_tickers() -> set:
    """etfs 테이블에 등록된 종목 티커 set 반환"""
    with get_db_connection() as conn_or_cursor:
        cursor = get_cursor(conn_or_cursor)
        cursor.execute("SELECT ticker FROM etfs")
        return {row['ticker'] if USE_POSTGRES else row[0] for row in cursor.fetchall()}


@router.get("", response_model=ScreeningResponse)
async def search_screening(
    q: Optional[str] = Query(None, description="종목명/코드 검색"),
    type: str = Query("ETF", description="ETF / STOCK / ALL"),
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
        "screening", q=q, type=type, sector=sector,
        min_wr=min_weekly_return, max_wr=max_weekly_return,
        fnp=foreign_net_positive, inp=institutional_net_positive,
        sort_by=sort_by, sort_dir=sort_dir, page=page, page_size=page_size
    )
    cached = cache.get(cache_key)
    if cached:
        return cached

    p = "%s" if USE_POSTGRES else "?"

    where_clauses = ["sc.is_active = 1"]
    params = []

    if type != "ALL":
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

    # 정렬 컬럼 화이트리스트
    allowed_sort = {
        "weekly_return", "daily_change_pct", "volume",
        "close_price", "foreign_net", "institutional_net", "name"
    }
    if sort_by not in allowed_sort:
        sort_by = "weekly_return"
    sort_dir_sql = "ASC" if sort_dir == "asc" else "DESC"

    # NULLS LAST 처리
    if USE_POSTGRES:
        nulls_last = "NULLS LAST"
    else:
        nulls_last = ""
        # SQLite: NULL은 기본적으로 마지막에 옴 (DESC 시에는 CASE로 처리)

    registered_tickers = _get_registered_tickers()

    with get_db_connection() as conn_or_cursor:
        cursor = get_cursor(conn_or_cursor)

        # 전체 건수
        cursor.execute(f"SELECT COUNT(*) as cnt FROM stock_catalog sc WHERE {where_sql}", params)
        row = cursor.fetchone()
        total = row['cnt'] if USE_POSTGRES else row[0]

        # 데이터 조회
        offset = (page - 1) * page_size
        query_params = params + [page_size, offset]

        if USE_POSTGRES:
            order_clause = f"sc.{sort_by} {sort_dir_sql} {nulls_last}"
        else:
            # SQLite NULL 처리
            order_clause = f"CASE WHEN sc.{sort_by} IS NULL THEN 1 ELSE 0 END, sc.{sort_by} {sort_dir_sql}"

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
    cache.set(cache_key, result, ttl_seconds=SCREENING_CACHE_TTL)
    return result


@router.get("/themes", response_model=List[ThemeGroup])
async def get_themes():
    """섹터/테마별 그룹 조회"""
    cache = get_cache()
    cache_key = "screening:themes"
    cached = cache.get(cache_key)
    if cached:
        return cached

    p = "%s" if USE_POSTGRES else "?"
    registered_tickers = _get_registered_tickers()

    with get_db_connection() as conn_or_cursor:
        cursor = get_cursor(conn_or_cursor)

        # 섹터별 집계
        cursor.execute("""
            SELECT sector, COUNT(*) as cnt,
                   AVG(weekly_return) as avg_wr
            FROM stock_catalog
            WHERE is_active = 1
              AND sector IS NOT NULL
              AND sector != ''
              AND catalog_updated_at IS NOT NULL
            GROUP BY sector
            ORDER BY avg_wr DESC
        """)

        sectors = [dict(row) for row in cursor.fetchall()]

        themes = []
        for s in sectors:
            sector_name = s['sector']
            avg_wr = s.get('avg_wr')

            # 섹터 내 top 3 종목
            cursor.execute(f"""
                SELECT ticker, name, type, market, sector,
                       close_price, daily_change_pct, volume,
                       weekly_return, foreign_net, institutional_net,
                       catalog_updated_at
                FROM stock_catalog
                WHERE is_active = 1
                  AND sector = {p}
                  AND catalog_updated_at IS NOT NULL
                ORDER BY CASE WHEN weekly_return IS NULL THEN 1 ELSE 0 END,
                         weekly_return DESC
                LIMIT 3
            """, (sector_name,))

            top_rows = cursor.fetchall()
            top_items = [_row_to_screening_item(dict(r), registered_tickers) for r in top_rows]

            themes.append(ThemeGroup(
                sector=sector_name,
                count=s['cnt'],
                avg_weekly_return=round(avg_wr, 2) if avg_wr is not None else None,
                top_performers=top_items
            ))

    cache.set(cache_key, themes, ttl_seconds=SCREENING_CACHE_TTL)
    return themes


@router.get("/recommendations", response_model=List[RecommendationPreset])
async def get_recommendations(
    limit: int = Query(5, ge=1, le=10, description="각 프리셋별 종목 수")
):
    """추천 프리셋 (주간 상위, 외국인 매수 등)"""
    cache = get_cache()
    cache_key = f"screening:recommendations:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    p = "%s" if USE_POSTGRES else "?"
    registered_tickers = _get_registered_tickers()

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
                WHERE is_active = 1
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

    cache.set(cache_key, results, ttl_seconds=SCREENING_CACHE_TTL)
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

    collector = CatalogDataCollector()

    background_tasks.add_task(collector.collect_all)

    return {"message": "카탈로그 데이터 수집이 시작되었습니다", "status": "started"}
