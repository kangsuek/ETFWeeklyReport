# 시스템 아키텍처

## 전체 구조

```
┌─────────────────┐         ┌──────────────────┐
│   Web Browser   │ ◄─────► │  React Frontend  │
│   (User)        │         │  (Port 5173)     │
└─────────────────┘         └──────────────────┘
                                      │
                                      │ HTTP/REST
                                      │
                            ┌─────────▼──────────┐
                            │  FastAPI Backend   │
                            │  (Port 8000)       │
                            └─────────┬──────────┘
                                      │
                ┌─────────────────────┼─────────────────────┐
                │                     │                     │
        ┌───────▼────────┐   ┌───────▼────────┐   ┌───────▼────────┐
        │  Data Collector│   │   Database     │   │  News Scraper  │
        │  (Naver Finance│   │   (SQLite)     │   │  (Naver News)  │
        │   스크래핑)     │   │                │   │                │
        └────────────────┘   └────────────────┘   └────────────────┘
```

## 백엔드 구조

### 디렉토리 구조

```
ETFWeeklyReport/
├── backend/                   # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py           # FastAPI 앱 진입점
│   │   ├── config.py         # 설정 관리
│   │   ├── database.py       # DB 연결 및 초기화
│   │   ├── models.py         # Pydantic 데이터 모델
│   │   ├── routers/          # API 라우터
│   │   │   ├── etfs.py      # ETF 관련 엔드포인트
│   │   │   ├── news.py      # 뉴스 관련 엔드포인트
│   │   │   └── reports.py   # 리포트 생성 엔드포인트
│   │   └── services/         # 비즈니스 로직
│   │       ├── data_collector.py # ETF 데이터 수집
│   │       └── news_scraper.py   # 뉴스 스크래핑
│   ├── data/                 # SQLite 데이터베이스 파일
│   ├── tests/                # 테스트 코드
│   ├── requirements.txt      # Python 의존성
│   └── Dockerfile           # Docker 설정
├── frontend/                 # React 프론트엔드
├── docker-compose.yml        # Docker Compose 설정
└── docs/                     # 프로젝트 문서
```

### 백엔드 레이어

1. **API Layer** (routers/)
   - HTTP 요청 처리
   - 입력 검증
   - 응답 포매팅

2. **Service Layer** (services/)
   - 비즈니스 로직
   - 데이터 수집 및 가공
   - 외부 API 호출

3. **Data Layer** (database.py, models.py)
   - 데이터베이스 연결
   - 데이터 모델 정의
   - CRUD 작업

## 프론트엔드 구조

### 디렉토리 구조

```
frontend/
├── src/
│   ├── main.jsx               # React 진입점
│   ├── App.jsx                # 라우팅 설정
│   ├── pages/                 # 페이지 컴포넌트
│   │   ├── Dashboard.jsx     # 메인 대시보드
│   │   ├── ETFDetail.jsx     # ETF 상세 페이지
│   │   └── Comparison.jsx    # 비교 페이지
│   ├── components/            # 재사용 컴포넌트
│   │   ├── layout/           # Header, Footer 등
│   │   ├── etf/              # ETF 관련 컴포넌트
│   │   ├── charts/           # 차트 컴포넌트
│   │   └── common/           # 공통 컴포넌트
│   ├── hooks/                # Custom React Hooks
│   ├── services/             # API 클라이언트
│   │   └── api.js
│   ├── utils/                # 유틸리티 함수
│   └── styles/               # 스타일 파일
│       └── index.css
├── public/                    # 정적 파일
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── Dockerfile
```

### 프론트엔드 패턴

1. **컴포넌트 구조**
   - Pages: 라우트 레벨 컴포넌트
   - Components: 재사용 가능한 컴포넌트
   - Layouts: 공통 레이아웃 컴포넌트

2. **상태 관리**
   - TanStack Query (React Query): 서버 상태
   - React Hooks (useState, useEffect): 로컬 상태

3. **스타일링**
   - TailwindCSS: 유틸리티 우선 CSS
   - 모바일 우선 반응형 디자인

## 데이터 흐름

### 데이터 수집 흐름 ✅ Phase 1 완료

```
1. 스케줄러 (매일 장 마감 후 3:30 PM KST) [Phase 2 예정]
   OR
   수동 트리거 (POST /api/etfs/{ticker}/collect) ✅
   ↓
2. Data Collector Service ✅
   - 종목 존재 여부 확인
   - Rate Limiting (0.5초 대기)
   ↓
3. Naver Finance 웹 스크래핑 ✅
   - URL: https://finance.naver.com/item/sise_day.naver?code={종목코드}
   - 대상: 6개 종목 (ETF 4개 + 주식 2개)
     * 487240: KODEX AI전력핵심설비
     * 466920: SOL 조선TOP3플러스
     * 0020H0: 글로벌양자컴퓨팅액티브
     * 442320: RISE 글로벌원자력 iSelect
     * 042660: 한화오션
     * 034020: 두산에너빌리티
   ↓
4. HTML 파싱 (BeautifulSoup4) ✅
   - table.type2에서 일별 데이터 추출
   - 필드: 날짜, 시가, 고가, 저가, 종가, 거래량, 등락률
   ↓
5. 데이터 검증 및 정제 ✅
   - 필수 필드 검증 (ticker, date, close_price)
   - 날짜 형식 검증 (YYYY-MM-DD)
   - 가격/거래량 범위 검증 (양수, 논리적 관계)
   - 데이터 타입 변환 및 정규화
   - 결측치 처리 (None 허용)
   ↓
6. Database 저장 (SQLite) ✅
   - INSERT OR REPLACE (중복 방지)
   - 트랜잭션 관리
   - 저장 성공/실패 로깅
```

#### 구현된 기능 (Phase 1)
- ✅ Naver Finance 스크래핑 (`fetch_naver_finance_prices`)
- ✅ 데이터 검증 (`validate_price_data`)
- ✅ 데이터 정제 (`clean_price_data`)
- ✅ 데이터베이스 저장 (`save_price_data`)
- ✅ 통합 수집 함수 (`collect_and_save_prices`)
- ✅ API 엔드포인트 (POST `/api/etfs/{ticker}/collect`)
- ✅ 61개 테스트 100% 통과

### API 요청 흐름

```
1. Frontend (React)
   ↓
2. Axios HTTP Request
   ↓
3. FastAPI Router
   ↓
4. Service Layer
   ↓
5. Database Query
   ↓
6. Response (JSON)
   ↓
7. React Query Cache
   ↓
8. UI 렌더링
```

## 배포 아키텍처

### 개발 환경

```
Developer Machine
├── Backend: localhost:8000
├── Frontend: localhost:5173
└── Database: SQLite (local file)
```

### 프로덕션 환경 (권장)

```
┌─────────────────────────────────────┐
│         CDN (Vercel/Netlify)       │  ← Frontend (React SPA)
└─────────────────┬───────────────────┘
                  │ HTTPS
                  ▼
┌─────────────────────────────────────┐
│    Backend API (Render/Railway)     │  ← FastAPI Server
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│      PostgreSQL Database            │  ← Managed DB Service
└─────────────────────────────────────┘
```

### Docker 배포

```
Docker Host
├── Backend Container (port 8000)
├── Frontend Container (port 5173)
└── PostgreSQL Container (port 5432)
```

## 보안 고려사항

1. **CORS 설정**: 허용된 origin만 접근 가능
2. **입력 검증**: Pydantic을 통한 자동 검증
3. **환경 변수**: 민감한 정보는 .env 파일로 관리
4. **Rate Limiting**: API 엔드포인트 호출 제한 (추후 구현)
5. **HTTPS**: 프로덕션 환경에서 필수

## 성능 최적화

### 백엔드

- **비동기 처리**: async/await 사용
- **캐싱**: Redis (선택사항, 프로덕션)
- **연결 풀**: 데이터베이스 연결 재사용
- **인덱싱**: 자주 조회하는 컬럼에 인덱스 생성

### 프론트엔드

- **Code Splitting**: React.lazy로 청크 분할
- **이미지 최적화**: WebP 포맷 사용
- **React.memo**: 불필요한 리렌더링 방지
- **Virtual Scrolling**: 대용량 테이블 처리
- **Debouncing**: 검색 입력 최적화

## 모니터링 및 로깅

### 백엔드 로깅

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 추적할 메트릭

- API 응답 시간
- 데이터 수집 성공/실패율
- 데이터베이스 쿼리 성능
- 엔드포인트별 에러율
- 사용자 활동 (선택사항)

---
