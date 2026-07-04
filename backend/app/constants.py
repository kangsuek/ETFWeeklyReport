"""
Application-wide constants

This module defines constants used throughout the application to avoid magic numbers
and improve code maintainability.

매직 넘버(Magic Number)란?
코드에 직접 쓰인 숫자로, 의미를 알기 어렵고 유지보수가 어려운 값입니다.
예: volatility = std_dev * math.sqrt(252)  # 252가 무엇을 의미하는지 불명확

이 파일에 정의된 상수를 사용하면:
- 코드 가독성 향상: 숫자의 의미가 명확해짐
- 유지보수 용이: 한 곳에서 값을 변경하면 전체 적용
- 버그 감소: 같은 값을 여러 곳에 입력하다 실수하는 것을 방지
"""

# =============================================================================
# 날짜 및 시간 관련 상수
# =============================================================================

DAYS_IN_YEAR = 365
"""
1년의 일수 (365일)

용도:
- 1년치 데이터 조회 시 날짜 범위 계산
- 예: one_year_ago = today - timedelta(days=DAYS_IN_YEAR)

왜 365일인가?
- 일반적인 1년의 일수 (윤년 제외)
- 금융 데이터 분석에서 표준으로 사용
"""

TRADING_DAYS_PER_YEAR = 252
"""
연간 거래일수 (252일)

용도:
- 일간 변동성을 연간 변동성으로 환산할 때 사용
- 예: annual_volatility = daily_std * sqrt(TRADING_DAYS_PER_YEAR)

왜 252일인가?
- 1년 365일 - 주말 104일 - 공휴일 약 9일 = 252일
- 한국 증시 기준 실제 거래일수와 근사
- 금융 업계 표준 (국제적으로 통용되는 값)

참고:
- 미국: 약 252일 (공휴일 9일)
- 한국: 약 245-250일 (공휴일 더 많음, 하지만 252를 표준으로 사용)
"""

# =============================================================================
# 데이터 수집 관련 상수
# =============================================================================

MAX_COLLECTION_DAYS = 365
"""
API 1회 요청당 최대 수집 가능 일수 (365일 = 1년)

용도:
- 백필(backfill) 또는 대량 수집 시 최대 범위 제한
- API Query validation: ge=1, le=MAX_COLLECTION_DAYS

왜 365일로 제한하는가?
- 네이버 금융 스크래핑 부하 방지
- 데이터베이스 트랜잭션 크기 제한
- 메모리 사용량 제어 (1년치 = 약 252건)
- 1년 이상 데이터는 여러 번 나눠서 수집 권장

변경 시 고려사항:
- 값을 늘리면 한 번에 더 많은 데이터 수집 가능하지만,
- 스크래핑 서버 부하 증가 및 응답 시간 지연 가능
"""

DEFAULT_BACKFILL_DAYS = 90
"""
히스토리 백필 시 기본 수집 일수 (90일 = 약 3개월)

용도:
- /api/data/backfill 엔드포인트의 기본값
- 초기 데이터베이스 구축 시 사용

왜 90일인가?
- 단기 트렌드 파악에 충분한 기간 (약 3개월)
- 분기(Quarter) 단위 분석 가능
- 너무 길면 초기 로딩 시간 증가
- 너무 짧으면 의미 있는 패턴 발견 어려움

사용 예:
- 신규 종목 추가 시 최근 3개월 데이터 자동 수집
- 주말에 자동 백필 작업 실행
"""

DEFAULT_COLLECTION_DAYS = 1
"""
일반 데이터 수집 시 기본 일수 (1일 = 당일만)

용도:
- /api/data/collect-all 엔드포인트의 기본값
- 스케줄러의 주기적 수집 기본값

왜 1일인가?
- 실시간성: 가장 최근 데이터만 수집 (빠른 업데이트)
- 부하 최소화: 스크래핑 대상 최소화
- 일반적으로 당일 데이터만 필요 (과거 데이터는 이미 DB에 존재)

사용 예:
- 매 6분마다 실행되는 자동 수집 (당일 데이터만 갱신)
- 수동 데이터 갱신 요청 시 기본값
"""

# =============================================================================
# 퍼센트 계산 상수
# =============================================================================

PERCENT_MULTIPLIER = 100
"""
비율을 백분율(%)로 변환하는 승수 (100)

용도:
- 수익률 계산: return_pct = (price_new - price_old) / price_old * PERCENT_MULTIPLIER
- 등락률 표시: change_pct = (change / prev_price) * PERCENT_MULTIPLIER

왜 100인가?
- 0.05 → 5% 로 변환 (사용자 친화적)
- 금융 데이터 표준 표기법

예:
- 수익률 0.15 → 15% (15% 상승)
- 수익률 -0.03 → -3% (3% 하락)
"""

# =============================================================================
# Rate Limiter 관련 상수
# =============================================================================

DEFAULT_RATE_LIMITER_INTERVAL = 0.3
"""
기본 Rate Limiter 간격 (0.3초)

용도:
- 스크래핑 요청 간 최소 대기 시간
- 네이버 금융 서버 부하 방지
- RateLimiter 초기화 시 기본값

왜 0.3초인가?
- 네이버 금융 서버 부하를 방지하면서 수집 속도 확보
- RateLimiter가 Lock 밖에서 sleep하므로 스레드별 동시 대기 가능
- 요청 간 최소 간격 0.3초 = 초당 ~3.3 요청 (IP 차단 임계치 이하)

사용 예:
- ETFDataCollector: min_interval=DEFAULT_RATE_LIMITER_INTERVAL
- TickerScraper: min_interval=DEFAULT_RATE_LIMITER_INTERVAL
"""

NEWS_RATE_LIMITER_INTERVAL = 0.1
"""
뉴스 API Rate Limiter 간격 (0.1초)

용도:
- 네이버 뉴스 API 요청 간 최소 대기 시간
- NewsScraper에서 사용

왜 0.1초인가?
- 네이버 검색 API는 공식 API이므로 더 짧은 간격 허용
- 공식 API는 Rate Limit이 더 관대함
- 빠른 수집이 가능하지만 여전히 서버 부하 방지

참고:
- 공식 API와 비공식 스크래핑의 차이
- 공식 API는 더 짧은 간격 허용 가능
"""

# =============================================================================
# 에러 메시지 상수
# =============================================================================

# 데이터베이스 관련 에러
ERROR_DATABASE = "데이터베이스 오류가 발생했습니다."
ERROR_DATABASE_COLLECTION = "데이터 수집 중 데이터베이스 오류가 발생했습니다."
ERROR_DATABASE_BACKFILL = "백필 중 데이터베이스 오류가 발생했습니다."
ERROR_DATABASE_RESET = "데이터베이스 초기화 중 오류가 발생했습니다."

# 검증 관련 에러
ERROR_VALIDATION = "입력값이 올바르지 않습니다."
ERROR_VALIDATION_TICKER = "종목 코드 형식이 올바르지 않습니다."
ERROR_VALIDATION_DATE_RANGE = "날짜 범위가 올바르지 않습니다."
ERROR_VALIDATION_COLLECTION_PARAMS = "수집 파라미터가 올바르지 않습니다."
ERROR_VALIDATION_BACKFILL_PARAMS = "백필 파라미터가 올바르지 않습니다."

# 외부 서비스 관련 에러
ERROR_SCRAPER = "데이터 소스에 일시적으로 접근할 수 없습니다."
ERROR_SCRAPER_COLLECTION = "데이터 수집에 실패했습니다. 데이터 소스가 일시적으로 사용 불가능할 수 있습니다."
ERROR_SCRAPER_NEWS = "뉴스 소스에 일시적으로 접근할 수 없습니다."

# 일반 서버 에러
ERROR_INTERNAL = "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
ERROR_INTERNAL_COLLECTION = "데이터 수집에 실패했습니다. 잠시 후 다시 시도해주세요."
ERROR_INTERNAL_BACKFILL = "백필에 실패했습니다. 잠시 후 다시 시도해주세요."
ERROR_INTERNAL_FETCH_PRICES = "가격 데이터 조회에 실패했습니다. 잠시 후 다시 시도해주세요."
ERROR_INTERNAL_FETCH_TRADING_FLOW = "매매 동향 조회에 실패했습니다. 잠시 후 다시 시도해주세요."
ERROR_INTERNAL_FETCH_NEWS = "뉴스 조회에 실패했습니다. 잠시 후 다시 시도해주세요."
ERROR_INTERNAL_FETCH_METRICS = "지표 조회에 실패했습니다. 잠시 후 다시 시도해주세요."
ERROR_INTERNAL_COMPARE = "종목 비교에 실패했습니다. 잠시 후 다시 시도해주세요."
ERROR_INTERNAL_GET_STATUS = "상태 조회에 실패했습니다. 잠시 후 다시 시도해주세요."
ERROR_INTERNAL_GET_SCHEDULER_STATUS = "스케줄러 상태 조회에 실패했습니다. 잠시 후 다시 시도해주세요."
ERROR_INTERNAL_GET_STATS = "통계 조회에 실패했습니다. 잠시 후 다시 시도해주세요."
ERROR_INTERNAL_RESET = "데이터베이스 초기화에 실패했습니다. 잠시 후 다시 시도해주세요."

# =============================================================================
# 캐시 TTL (Time To Live) 상수
# =============================================================================

# 엔드포인트별 차등 TTL (초 단위)
CACHE_TTL_STATIC = 300  # 5분
"""
정적 데이터 캐시 TTL (5분 = 300초)

적용 대상:
- GET /api/etfs/ (전체 종목 목록)
- GET /api/etfs/{ticker} (종목 상세)

왜 5분인가?
- 종목 정보는 거의 변경되지 않음 (이름, 타입, 테마 등)
- 긴 TTL로 DB 부하 최소화
- 5분마다 갱신되어도 충분히 실시간성 유지
"""

CACHE_TTL_FAST_CHANGING = 30  # 30초
"""
빠르게 변하는 데이터 캐시 TTL (30초)

적용 대상:
- GET /api/etfs/{ticker}/prices (가격 데이터)
- GET /api/etfs/{ticker}/trading-flow (매매동향)
- POST /api/etfs/batch-summary (배치 요약)

왜 30초인가?
- 실시간 가격 데이터는 자주 변경됨
- 30초 이내 동일 요청 시 불필요한 DB 조회 방지
- 대시보드 초기 로딩 시 반복 요청 방지
"""

CACHE_TTL_SLOW_CHANGING = 60  # 1분
"""
천천히 변하는 데이터 캐시 TTL (1분 = 60초)

적용 대상:
- GET /api/news/{ticker} (뉴스)
- GET /api/etfs/{ticker}/metrics (지표)
- POST /api/etfs/compare (종목 비교)

왜 1분인가?
- 뉴스는 실시간으로 갱신되지 않음 (1분마다 체크해도 충분)
- 지표는 가격 기반으로 계산되지만 자주 조회되므로 캐싱 효과 큼
- 비교 API는 복잡한 연산이므로 긴 TTL로 성능 향상
"""

CACHE_TTL_STATUS = 10  # 10초
"""
상태 정보 캐시 TTL (10초)

적용 대상:
- GET /api/data/status (수집 상태)
- GET /api/data/scheduler-status (스케줄러 상태)

왜 10초인가?
- 상태 정보는 자주 변경되지 않음
- 10초마다 폴링해도 충분히 실시간성 유지
- 짧은 TTL로 최신 상태 반영
"""

CACHE_TTL_STATS = 60  # 1분
"""
통계 정보 캐시 TTL (1분 = 60초)

적용 대상:
- GET /api/data/stats (전체 통계)

왜 1분인가?
- 통계는 즉시 변경되지 않음
- 복잡한 집계 쿼리이므로 긴 TTL로 성능 향상
- 1분마다 갱신되어도 충분
"""

# =============================================================================
# 상승흐름 신호 관련 상수 (docs/UPTREND_SIGNAL_DESIGN.md §2-6)
# =============================================================================
# 나머지 SIGNAL_* 상수(LOOKBACK/VOL_MULT/CONFIRM 등)는 Phase 2.1에서 추가된다.
# 감지기 판정용 최소 이력 일수는 갭 보충 헬퍼(Phase 1.1)가 먼저 필요로 하므로
# 여기서 선행 정의한다.

SIGNAL_MIN_DATA_DAYS = 30
"""
신호 감지에 필요한 최소 가격 이력 행 수 (거래일 기준, 약 6주)

용도:
- ensure_recent_history()가 갭 보충 후 이력 충분성을 판정하는 기준
- Donchian 20일 채널 + 5일 과열 판정 등에 필요한 최소 표본 확보

왜 30인가?
- 20일 채널을 계산하려면 최소 20행 + 판정 여유가 필요
- 30행이면 채널 계산과 최근 흐름 판정에 충분한 표본
"""
