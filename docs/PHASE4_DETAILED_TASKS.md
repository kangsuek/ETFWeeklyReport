# Phase 4: Charts & Visualization - 상세 작업 가이드

## 📋 Phase 4 개요

**목표**: 종목 데이터를 시각적으로 표현하는 차트 및 시각화 기능 구현

**현재 상태**: ✅ 기본 기능 완료 (가격 차트, 매매동향 차트, 날짜 선택기)

**추가 개선 필요**: 전문 애널리스트 리포트 수준의 인사이트 제공

## ✅ Phase 4.1 완료 (2025-01-27)

**완료된 작업**:
- ✅ 핵심 인사이트 블록 추가 (전략 요약, 핵심 포인트, 리스크)
- ✅ 수익률 지표 정교화 (연환산 수익률 개선, 변동성, MDD)
- ✅ UX 구조 개선 (레이아웃 재구성)

**상세 내용**: [PHASE4_IMPLEMENTATION_STATUS.md](./PHASE4_IMPLEMENTATION_STATUS.md) 참조

## ✅ 작업 완료 현황

### 완료된 작업 (2025-01-27)
- ✅ **핵심 인사이트 블록 추가** (1.1, 1.2, 1.3)
  - 백엔드: `app/services/insights_service.py` 생성
  - 백엔드: `/api/etfs/{ticker}/insights` 엔드포인트 추가
  - 프론트엔드: `components/etf/StrategySummary.jsx` 생성
  - 프론트엔드: `pages/ETFDetail.jsx`에 통합
  - 테스트: `tests/test_insights_service.py` 작성
  - 문서: API 명세 및 기능 문서 업데이트

---

## ✅ 작업 완료 현황

### Phase 4.1 완료 (2025-01-27)

#### ✅ 1. 핵심 인사이트 블록 추가 (1.1, 1.2, 1.3) - 완료

**백엔드:**
- ✅ `backend/app/services/insights_service.py` 생성
  - `InsightsService` 클래스 구현
  - 전략 분석, 핵심 포인트 추출, 리스크 분석 로직
- ✅ `backend/app/models.py` 업데이트
  - `StrategyInsights`, `ETFInsights` 모델 추가
- ✅ `backend/app/routers/etfs.py` 업데이트
  - `GET /api/etfs/{ticker}/insights` 엔드포인트 추가
- ✅ `backend/tests/test_insights_service.py` 작성
  - 5개 테스트 케이스 작성

**프론트엔드:**
- ✅ `frontend/src/components/etf/StrategySummary.jsx` 생성
  - 투자 전략 표시 (단기/중기/장기)
  - 종합 추천 및 코멘트
  - 핵심 포인트 리스트 (최대 3개)
  - 리스크 요약 리스트 (최대 3개)
- ✅ `frontend/src/services/api.js` 업데이트
  - `etfApi.getInsights()` 메서드 추가
- ✅ `frontend/src/pages/ETFDetail.jsx` 업데이트
  - `StrategySummary` 컴포넌트 통합

**문서:**
- ✅ `docs/API_SPECIFICATION.md` 업데이트
- ✅ `docs/FEATURES.md` 업데이트
- ✅ `docs/PHASE4_IMPLEMENTATION_STATUS.md` 생성
- ✅ `docs/PHASE4_DETAILED_TASKS.md` 업데이트

**상세 내용**: [PHASE4_IMPLEMENTATION_STATUS.md](./PHASE4_IMPLEMENTATION_STATUS.md) 참조

#### ✅ 2. 수익률 지표 정교화 (2.1, 2.2) - 완료
- ✅ 연환산 수익률 개선: 3개월 미만 데이터는 연환산 표기 안 함
- ✅ 변동성 및 Max Drawdown 표시 추가
- ✅ 백엔드 metrics API 확장
- ✅ 프론트엔드 StatsSummary 컴포넌트 개선
- ✅ ComparisonTable 연환산 수익률 표시 개선

#### ✅ 3. UX 구조 개선 (5.1) - 완료
- ✅ 레이아웃 재구성: 투자 의견 → 성과 지표 → 차트 → 뉴스 순서
- ✅ ETFDetail 페이지 레이아웃 최적화

---

## ✅ 이미 완료된 작업

### 1. 기본 차트 컴포넌트
- ✅ **PriceChart**: 가격 차트 (캔들스틱, 이동평균선, 거래량)
- ✅ **TradingFlowChart**: 투자자별 매매동향 차트
- ✅ **IntradayChart**: 분봉(시간별) 차트
- ✅ **DateRangeSelector**: 날짜 범위 선택기

### 2. 차트 기능
- ✅ 반응형 디자인 (모바일/태블릿/데스크탑)
- ✅ 다크 모드 지원
- ✅ 스크롤 동기화 (가격 차트 ↔ 매매동향 차트)
- ✅ 커스텀 툴팁
- ✅ 이동평균선 (MA5, MA10, MA20) 토글
- ✅ 매입가 표시 (ReferenceLine)

### 3. 테스트
- ✅ PriceChart.test.jsx
- ✅ TradingFlowChart.test.jsx
- ✅ DateRangeSelector.test.jsx

---

## 🎯 Phase 4에서 추가로 해야 할 작업

### 1. 핵심 인사이트 블록 추가 (우선순위: 높음) ✅ **완료** (2025-01-27)

#### 1.1 전략 요약 섹션 ✅
**위치**: 종목 상세 페이지 상단 (ETFHeader 아래)

**구현 내용**:
```jsx
// components/etf/StrategySummary.jsx
- 단기/중기/장기 투자 의견
- 투자 비중 제안 (비중확대/보유/축소)
- 한 줄 코멘트
```

**데이터 소스**:
- 백엔드: `/api/etfs/{ticker}/insights` 엔드포인트 추가 필요
- 또는 프론트엔드에서 계산 (수익률, 변동성 기반)

**API 설계**:
```python
# backend/app/routers/etfs.py
@router.get("/{ticker}/insights")
async def get_etf_insights(
    etf: ETF = Depends(get_etf_or_404),
    period: str = Query("1m", description="기간: 1w, 1m, 3m, 6m, 1y")
):
    """
    종목 인사이트 생성
    
    Returns:
    {
        "strategy": {
            "short_term": "관망",  # 단기 (1주)
            "medium_term": "비중확대",  # 중기 (1-3개월)
            "long_term": "보유",  # 장기 (6개월+)
            "recommendation": "비중확대",
            "comment": "단기 급등 구간, 변동성 확대 예상"
        },
        "key_points": [
            "단기 급등 구간, 변동성 확대 예상",
            "미국 관세 리스크 부각",
            "국내 메모리 업황 턴어라운드 초기"
        ],
        "risks": [
            "규제 리스크: 반도체 수출 규제 가능성",
            "사이클 피크: 메모리 가격 상승세 둔화 우려",
            "환율 리스크: 원/달러 환율 변동성 확대"
        ]
    }
    """
```

**구현 단계**:
1. ✅ 백엔드 인사이트 서비스 생성 (`app/services/insights_service.py`) - **완료**
2. ✅ 인사이트 계산 로직 구현 (수익률, 변동성, 뉴스 센티먼트 기반) - **완료**
3. ✅ 프론트엔드 StrategySummary 컴포넌트 생성 - **완료**
4. ✅ ETFDetail 페이지에 통합 - **완료**
5. ✅ 테스트 작성 (`tests/test_insights_service.py`) - **완료**

---

#### 1.2 핵심 포인트 3개 표시 ✅
**위치**: StrategySummary 내부

**구현 내용**:
- 최근 데이터 기반 핵심 포인트 자동 생성
- 예시:
  - "단기 급등 구간, 변동성 확대 예상"
  - "미국 관세 리스크 부각"
  - "국내 메모리 업황 턴어라운드 초기"

**데이터 소스**:
- 가격 변동성 분석
- 뉴스 키워드 분석
- 매매동향 패턴 분석

---

#### 1.3 리스크 요약 ✅
**위치**: StrategySummary 내부

**구현 내용**:
- 규제 리스크
- 사이클 피크 가능성
- 환율/금리 리스크
- 섹터별 특수 리스크

**데이터 소스**:
- 뉴스 키워드 분석 (규제, 관세 등)
- 환율/금리 데이터 (외부 API 또는 수동 입력)
- 섹터별 리스크 데이터베이스

---

### 2. 수익률·리스크 지표 정교화 (우선순위: 높음) ✅ **완료** (2025-01-27)

#### 2.1 연환산 수익률 개선 ✅
**문제점**: 1개월 데이터로 연환산 시 2,000%대 과장된 수치

**해결 방안**: ✅ 구현 완료
```jsx
// utils/returns.js 개선
export function formatAnnualizedReturn(returnPct, days) {
  if (days < 90) {
    // 3개월 미만은 연환산 표기 안 함
    return {
      value: returnPct,
      label: `${days}일 수익률`,
      showAnnualized: false
    }
  }
  // 3개월 이상만 연환산 표시
  return {
    value: annualizedReturn,
    label: "연환산 수익률",
    showAnnualized: true,
    note: "참고용"
  }
}
```

**구현 위치**: ✅ 완료
- ✅ `frontend/src/utils/returns.js` - `calculateAnnualizedReturn` 함수 개선 (3개월 미만은 연환산 표기 안 함)
- ✅ `frontend/src/components/etf/StatsSummary.jsx` - 연환산 수익률 조건부 표시
- ✅ `frontend/src/components/comparison/ComparisonTable.jsx` - 연환산 수익률 N/A 처리
- ✅ `backend/app/services/comparison_service.py` - `calculate_annualized_return` 함수 개선 (3개월 미만은 None 반환)

---

#### 2.2 변동성·Max Drawdown 표시 ✅
**구현 내용**: ✅ 구현 완료
- 일간 수익률 표준편차
- 최대 낙폭 (MDD)
- 베타 (시장 대비 변동성)

**백엔드 API 확장**:
```python
# backend/app/routers/etfs.py
@router.get("/{ticker}/metrics")
async def get_metrics(...):
    # 기존 코드에 추가
    return {
        ...
        "volatility": {
            "daily": 2.5,  # 일간 변동성 (%)
            "annualized": 39.8  # 연환산 변동성 (%)
        },
        "max_drawdown": -12.5,  # 최대 낙폭 (%)
        "beta": 1.2,  # 베타 (시장 대비)
        "sharpe_ratio": 1.67  # 샤프 비율
    }
```

**프론트엔드 표시**: ✅ 완료
- ✅ `components/etf/StatsSummary.jsx`에 리스크 지표 카드 추가
  - 연환산 변동성 표시 (색상 코딩: >30% 빨강, <15% 초록)
  - 최대 낙폭 (MDD) 표시
  - 일간 변동성 표시
- ✅ `backend/app/models.py` - `ETFMetrics` 모델에 `max_drawdown`, `sharpe_ratio` 필드 추가
- ✅ `backend/app/services/data_collector.py` - `get_etf_metrics` 메서드에 MDD, 샤프비율 계산 추가

---

#### 2.3 벤치마크 대비 분석
**구현 내용**:
- 코스피/코스닥 대비 상대수익률 (α)
- KOSPI200 대비
- 타 ETF 대비 (비교 페이지에서)

**데이터 소스**:
- 외부 API: 한국거래소 API 또는 FinanceDataReader
- 또는 수동 입력 (벤치마크 데이터)

**API 설계**:
```python
# backend/app/routers/etfs.py
@router.get("/{ticker}/benchmark-comparison")
async def get_benchmark_comparison(
    etf: ETF = Depends(get_etf_or_404),
    benchmark: str = Query("KOSPI", description="KOSPI, KOSDAQ, KOSPI200"),
    period: str = Query("1m")
):
    """
    벤치마크 대비 성과 비교
    
    Returns:
    {
        "ticker": "487240",
        "benchmark": "KOSPI",
        "period": "1m",
        "etf_return": 12.5,
        "benchmark_return": 8.3,
        "alpha": 4.2,  # 초과수익률
        "correlation": 0.85  # 상관계수
    }
    """
```

---

### 3. 섹터·펀더멘털 연계 분석 (우선순위: 중간)

#### 3.1 상위 편입 종목 Top 5 비중
**구현 내용**:
- ETF 구성종목 Top 5
- 비중 표시 (파이 차트 또는 막대 차트)
- 간단 코멘트 (팹/장비/소재 구성비 등)

**데이터 소스**:
- 네이버 금융 ETF 구성종목 페이지 스크래핑
- 또는 수동 입력 (stocks.json에 추가)

**API 설계**:
```python
# backend/app/routers/etfs.py
@router.get("/{ticker}/holdings")
async def get_etf_holdings(
    etf: ETF = Depends(get_etf_or_404)
):
    """
    ETF 구성종목 조회
    
    Returns:
    {
        "ticker": "487240",
        "holdings": [
            {
                "ticker": "005930",
                "name": "삼성전자",
                "weight": 25.5,  # 비중 (%)
                "category": "팹"  # 카테고리
            },
            ...
        ],
        "total_count": 50,
        "top5_weight": 65.2  # 상위 5개 비중 합계
    }
    """
```

**프론트엔드 컴포넌트**:
```jsx
// components/etf/HoldingsChart.jsx
- 파이 차트 또는 막대 차트
- Top 5 비중 표시
- 카테고리별 그룹핑
```

---

#### 3.2 업황 지표 연계
**구현 내용**:
- D램/낸드 가격 지수
- 글로벌 반도체 출하량
- SOX 지수와의 상관관계

**데이터 소스**:
- 외부 API (예: FRED API, Investing.com)
- 또는 수동 입력

**구현 우선순위**: 낮음 (외부 데이터 소스 확보 필요)

---

#### 3.3 환율·금리 연계
**구현 내용**:
- 달러/원 환율과 ETF 수익률 상관도
- 미국 10년물 금리와 상관도

**데이터 소스**:
- 한국은행 API 또는 수동 입력
- 상관계수 계산 (프론트엔드 또는 백엔드)

**구현 우선순위**: 중간

---

### 4. 뉴스 섹션 개선 (우선순위: 중간)

#### 4.1 뉴스 요약·태깅
**구현 내용**:
- 기사마다 1줄 요약
- 태그 (정책, 업황, 개별기업, 규제, 관세 리스크 등)

**백엔드 개선**:
```python
# backend/app/services/news_scraper.py
def _categorize_news(self, news_item: Dict) -> Dict:
    """
    뉴스 카테고리 및 태그 자동 분류
    
    Returns:
    {
        "category": "정책",  # 정책, 업황, 개별기업, 규제, 관세
        "tags": ["관세", "미국"],
        "summary": "미국 반도체 수출 규제 강화 발표..."
    }
    """
```

**프론트엔드 개선**:
```jsx
// components/news/NewsTimeline.jsx 개선
- 뉴스 카드에 태그 표시
- 요약 표시 (기사 제목 아래)
- 카테고리별 필터링
```

---

#### 4.2 센티먼트 표시
**구현 내용**:
- 기사별 긍정/부정/중립 표시
- 아이콘으로 표현 (↑, →, ↓)

**구현 방법**:
- 키워드 기반 센티먼트 분석 (간단)
- 또는 AI 기반 센티먼트 분석 (고급)

**백엔드**:
```python
# backend/app/services/news_scraper.py
def _analyze_sentiment(self, news_item: Dict) -> str:
    """
    뉴스 센티먼트 분석
    
    Returns: "positive", "neutral", "negative"
    """
    # 키워드 기반 간단 분석
    positive_keywords = ["상승", "증가", "호조", "성장"]
    negative_keywords = ["하락", "감소", "부진", "위축"]
    # ...
```

---

#### 4.3 테마 코멘트
**구현 내용**:
- "최근 3일간 뉴스는 미국 관세 압박 등 정책 리스크에 집중"
- 뉴스 묶음에 대한 한 줄 정리

**구현 위치**:
- `components/news/NewsTimeline.jsx` 상단
- 뉴스 목록 위에 요약 표시

---

### 5. UX·구조 개선 (우선순위: 중간) ✅ **완료** (2025-01-27)

#### 5.1 레이아웃 흐름 재구성 ✅
**현재 구조**:
1. 종목 요약
2. 가격 차트
3. 매매동향 차트
4. 뉴스

**개선된 구조**: ✅ 구현 완료
1. 종목 요약 (ETFHeader)
2. **투자 인사이트 요약** (InsightSummary)
3. **투자 의견·핵심 포인트** (StrategySummary) ✅ 신규
4. **성과 및 리스크 지표** (StatsSummary) ✅ 개선
5. 기본 정보 (종목 정보, 최근 가격)
6. 날짜 범위 선택기
7. 가격 차트
8. 매매동향 차트
9. 분봉 차트
10. 가격 데이터 테이블
11. 뉴스/이벤트

**구현 위치**: ✅ 완료
- ✅ `pages/ETFDetail.jsx` 레이아웃 재구성 완료

---

#### 5.2 숫자 강조 방식 개선
**구현 내용**:
- 매입가·현재가·수익률 색상/아이콘 강조
- 평가금액/손익 카드형으로 분리

**컴포넌트**:
```jsx
// components/etf/PriceHighlight.jsx
- 현재가: 큰 숫자, 색상 강조
- 수익률: 아이콘 (↑/↓) + 색상
- 평가금액/손익: 별도 카드
```

---

#### 5.3 기간 프리셋 확장
**현재**: 7일, 1개월, 3개월

**개선**: 1주, 1개월, 3개월, 6개월, YTD, 1년

**구현 위치**:
- `components/charts/DateRangeSelector.jsx` 확장

**연동 기능**:
- 기간 선택에 맞춰 통계 요약 자동 업데이트
- 뉴스 필터 자동 적용

---

### 6. 추가 차트 기능 (우선순위: 낮음)

#### 6.1 상관관계 차트
**구현 내용**:
- 비교 페이지에서 상관관계 히트맵
- 이미 API는 있음 (`/api/etfs/compare`)

**프론트엔드**:
```jsx
// components/comparison/CorrelationMatrix.jsx (신규)
- 히트맵 차트
- 상관계수 표시
```

---

#### 6.2 기술적 지표 차트
**구현 내용**:
- RSI (상대강도지수)
- MACD
- 볼린저 밴드

**우선순위**: 낮음 (고급 기능)

---

## 📝 구현 우선순위

### Phase 4.1 (즉시 구현)
1. ✅ **핵심 인사이트 블록 (전략 요약, 핵심 포인트, 리스크)** - **완료** ✅
   - ✅ 백엔드: `app/services/insights_service.py` 생성
   - ✅ 백엔드: `/api/etfs/{ticker}/insights` 엔드포인트 추가
   - ✅ 프론트엔드: `components/etf/StrategySummary.jsx` 생성
   - ✅ 프론트엔드: `pages/ETFDetail.jsx`에 통합
   - ✅ 테스트: `tests/test_insights_service.py` 작성
   - ⏳ 테스트 실행 및 검증 필요
2. ⏳ 수익률 지표 정교화 (연환산 수익률 개선, 변동성, MDD)
3. ⏳ UX 구조 개선 (레이아웃 재구성)

### Phase 4.2 (다음 단계)
4. ✅ 벤치마크 대비 분석
5. ✅ 뉴스 섹션 개선 (요약, 태깅, 센티먼트)
6. ✅ 기간 프리셋 확장

### Phase 4.3 (향후)
7. 섹터·펀더멘털 연계 분석 (외부 데이터 소스 확보 후)
8. 추가 차트 기능 (RSI, MACD 등)

---

## 🧪 테스트 요구사항

### 백엔드 테스트
- ✅ `test_insights_service.py` - 인사이트 서비스 테스트 (작성 완료)
- [ ] `test_benchmark_comparison.py` - 벤치마크 비교 테스트
- [ ] `test_holdings.py` - 구성종목 조회 테스트

### 프론트엔드 테스트
- ⏳ `StrategySummary.test.jsx` - 전략 요약 컴포넌트 테스트 (작성 필요)
- [ ] `HoldingsChart.test.jsx` - 구성종목 차트 테스트
- [ ] `NewsTimeline.test.jsx` - 뉴스 타임라인 개선 테스트

---

## 📊 API 명세 업데이트

Phase 4 작업 완료 후 다음 문서 업데이트 필요:
- ✅ `API_SPECIFICATION.md` - 새 엔드포인트 추가 (완료)
- ✅ `FEATURES.md` - 기능 상세 업데이트 (완료)
- ✅ `PHASE4_IMPLEMENTATION_STATUS.md` - 구현 상태 문서 생성 (완료)
- ⏳ `MILESTONES.md` - Phase 4 완료 상태 업데이트 (부분 완료)

---

## 🔗 관련 문서

- [FEATURES.md](./FEATURES.md) - 전체 기능 목록
- [API_SPECIFICATION.md](./API_SPECIFICATION.md) - API 명세
- [DEFINITION_OF_DONE.md](./DEFINITION_OF_DONE.md) - 완료 기준
- [PERPLEXITY_REPORT_IMPLEMENTATION.md](./PERPLEXITY_REPORT_IMPLEMENTATION.md) - 보고서 생성 기능

---

## 💡 참고사항

1. **외부 데이터 소스**: 벤치마크, 환율, 금리 데이터는 외부 API 필요
2. **AI 활용**: 뉴스 센티먼트 분석은 간단한 키워드 기반으로 시작, 향후 AI 모델 활용 가능
3. **성능**: 인사이트 계산은 캐싱 필수 (30초~1분 TTL)
4. **사용자 경험**: 전문 리포트 느낌을 위해 정보 밀도 높이기
