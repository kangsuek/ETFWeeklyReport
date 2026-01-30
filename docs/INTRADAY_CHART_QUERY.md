# 분봉 차트 조회 방식

## 개요

분봉 차트는 **주기적 자동 갱신 방식**입니다. 페이지 로드 시 호출되며, 30초마다 자동으로 갱신됩니다.

---

## 조회 흐름

### 1. 프론트엔드 (ETFDetail.jsx)

```javascript
// 페이지 로드 시 호출 + 30초마다 자동 갱신
{
  queryKey: ['intraday', ticker],
  queryFn: async () => {
    const response = await etfApi.getIntraday(ticker, { autoCollect: true })
    return response.data
  },
  staleTime: 30초,        // 30초 동안 fresh 상태
  refetchInterval: 30000,  // 30초마다 자동 갱신 ✅
  refetchOnMount: true,    // 컴포넌트 마운트 시 stale이면 갱신 ✅
}
```

**특징:**
- ✅ 페이지 로드 시 **1회 호출**
- ✅ **30초마다 자동 갱신** (`refetchInterval`)
- ✅ 컴포넌트 재마운트 시 stale이면 갱신 (`refetchOnMount`)
- ✅ `staleTime: 30초` - 30초 동안 캐시 사용
- ✅ 수동 새로고침 버튼 제공 (`refetchIntraday()`)

### 2. 백엔드 API (`GET /api/etfs/{ticker}/intraday`)

#### 조회 순서

```
1. 캐시 확인 (30초 TTL)
   ↓ (캐시 미스)
2. DB에서 데이터 조회
   ↓ (데이터 없음)
3. 마지막 거래일 데이터 확인
   ↓ (여전히 없음)
4. auto_collect=true인 경우 자동 수집
   - 네이버 금융 스크래핑
   - DB 저장
   - 다시 조회
```

#### 파라미터

- `target_date` (선택): 조회할 날짜 (기본: 오늘)
- `auto_collect` (기본: true): 데이터 없을 시 자동 수집 여부

#### 캐시 정책

- **TTL**: 30초 (`CACHE_TTL_FAST_CHANGING`)
- **키**: `intraday:{ticker}:{date}`
- **빈 결과**: 캐시하지 않음 (다음 요청에서 `auto_collect`가 다시 시도되도록 함. 프론트 새로고침/재진입 시 수집 트리거)

---

## 데이터 소스

### 1. DB 조회 (`intraday_prices` 테이블)

```sql
SELECT datetime, price, change_amount, volume, bid_volume, ask_volume
FROM intraday_prices
WHERE ticker = ? AND datetime BETWEEN '09:00' AND '15:30'
ORDER BY datetime ASC
```

### 2. 자동 수집 (데이터 없을 시)

- **소스**: 네이버 금융 시간별 체결 페이지
- **방식**: 웹 스크래핑 (Selenium/BeautifulSoup)
- **범위**: 당일 09:00 ~ 15:30 (약 390개 분봉)
- **트리거**: `auto_collect=true`이고 DB에 데이터 없을 때

---

## 자동 갱신 동작

### ✅ 주기적 자동 갱신

**설정:**
- `refetchInterval: 30000` (30초)
- `refetchOnMount: true` (컴포넌트 마운트 시)

**동작:**
1. 페이지 로드 시: 즉시 조회
2. 30초 후: 자동 갱신 (백그라운드)
3. 컴포넌트 재마운트 시: stale이면 갱신
4. 수동 새로고침: 버튼 클릭 시 즉시 갱신

### 캐시 동작

- **0-30초**: 캐시 사용 (API 호출 없음)
- **30초 후**: 자동 갱신 (백그라운드)
- **갱신 중**: 기존 데이터 표시 + "갱신 중..." 표시

---

## 성능 최적화

### 1. 캐싱

- **백엔드**: 30초 TTL (메모리 캐시)
- **프론트엔드**: 30초 `staleTime` (TanStack Query)
- **효과**: 동일 요청 시 DB 조회/네트워크 요청 생략

### 2. 자동 수집 최적화

- DB에 데이터 있으면 스크래핑 생략
- 마지막 거래일 자동 감지
- Rate Limiting 적용 (과도한 요청 방지)

### 3. 배치 처리

- 페이지 로드 시 다른 API와 **병렬 호출** (`useQueries`)
- 총 로딩 시간 = 가장 느린 API 시간

---

## 사용자 경험

### 현재 동작

1. **페이지 로드**: 분봉 데이터 즉시 조회 (병렬)
2. **30초마다**: 자동 갱신 (백그라운드)
3. **수동 갱신**: 새로고침 버튼 클릭 시 즉시 갱신
4. **자동 수집**: 데이터 없을 시 자동으로 네이버에서 수집

### 표시 상태

- **로딩 중**: 스피너 표시
- **갱신 중**: "갱신 중..." 텍스트 + 버튼 비활성화
- **데이터 없음**: "장중이 아니거나 휴장일입니다" 메시지

---

## 문제 해결 (2025-01-27)

### 이전 문제

- ❌ 30초 후 자동 갱신이 되지 않음
- ❌ `staleTime`만 설정하여 자동 refetch가 발생하지 않음

### 해결 방법

- ✅ `refetchInterval: 30000` 추가 - 30초마다 자동 갱신
- ✅ `refetchOnMount: true` 추가 - 컴포넌트 마운트 시 stale이면 갱신

### TanStack Query 동작 원리

- `staleTime`: 데이터가 "신선한" 것으로 간주되는 시간 (이 시간 동안은 refetch 안 함)
- `refetchInterval`: 주기적으로 자동 refetch (stale 여부와 무관)
- `refetchOnMount`: 컴포넌트 마운트 시 stale이면 refetch

**중요**: `staleTime`만 설정하면 자동 refetch가 발생하지 않습니다. `refetchInterval` 또는 `refetchOnMount`/`refetchOnWindowFocus`를 추가해야 합니다.

---

## 문제 해결 (2026-01-29): 프론트에서 분봉 수집이 안 되는 경우

### 이전 문제

- ✅ curl 등으로 `GET /api/etfs/{ticker}/intraday?auto_collect=true` 호출 시 수집 정상
- ❌ 종목 상세 페이지 진입 또는 분봉 새로고침 시 분봉 데이터가 수집되지 않음

### 원인

- 백엔드가 **빈 결과(데이터 없음)** 를 1분간 캐시함
- 이전 요청에서 빈 결과가 캐시된 뒤, 프론트 요청이 캐시 히트만 하고 DB 조회/자동 수집 로직에 도달하지 않음

### 해결 방법

1. **빈 결과 미캐시**: 백엔드에서 분봉 빈 응답을 캐시하지 않도록 변경. 다음 요청(페이지 진입·새로고침)에서 `auto_collect`가 다시 시도됨.
2. **타임아웃 확대**: 프론트 분봉 API 호출 타임아웃을 `LONG_API_TIMEOUT`(10분)으로 변경. 자동 수집(40페이지 스크래핑)이 60초 이상 걸릴 수 있어, 첫 요청에서 수집이 완료될 때까지 대기 가능.

---

## 요약

| 항목 | 내용 |
|------|------|
| **조회 방식** | 페이지 로드 시 1회, 30초마다 자동 갱신 |
| **실시간 여부** | ⚠️ 주기적 갱신 (30초 간격) |
| **캐시** | 백엔드 30초, 프론트엔드 30초 |
| **자동 수집** | ✅ DB에 데이터 없을 시 자동 수집 |
| **갱신 방법** | 자동 갱신 (30초) + 수동 새로고침 버튼 |
| **성능** | 병렬 호출, 캐싱으로 최적화 |
