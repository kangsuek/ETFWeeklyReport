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

```
backend/app/
├── main.py           # FastAPI 앱 진입점
├── config.py         # 설정 관리
├── database.py       # DB 연결 및 초기화
├── models.py         # Pydantic 데이터 모델
├── routers/          # API 라우터
│   ├── etfs.py      # ETF 관련 엔드포인트
│   ├── news.py      # 뉴스 관련 엔드포인트
│   └── reports.py   # 리포트 생성 엔드포인트
└── services/         # 비즈니스 로직
    ├── data_collector.py # ETF 데이터 수집
    └── news_scraper.py  # 뉴스 스크래핑
```

**레이어**: routers(HTTP) → services(로직) → database(DB)

## 프론트엔드 구조

```
frontend/src/
├── main.jsx         # React 진입점
├── App.jsx           # 라우팅 설정
├── pages/            # 라우트 컴포넌트
│   ├── Dashboard.jsx
│   ├── ETFDetail.jsx
│   └── Comparison.jsx
├── components/       # 재사용 컴포넌트
│   ├── layout/      # Header, Footer
│   ├── etf/         # ETF 관련
│   ├── charts/      # 차트 컴포넌트
│   └── common/      # 공통 컴포넌트
├── hooks/            # Custom React Hooks
├── services/         # API 클라이언트
└── utils/           # 유틸리티 함수
```

**패턴**: Pages → Components → Hooks → Services

## 데이터 흐름

### 데이터 수집 흐름
```
1. 스케줄러 (매일 15:30 KST) 또는 수동 트리거
   ↓
2. Data Collector Service
   ↓
3. Naver Finance 웹 스크래핑
   ↓
4. HTML 파싱 (BeautifulSoup4)
   ↓
5. 데이터 검증 및 정제
   ↓
6. Database 저장 (SQLite)
```

### API 요청 흐름
```
Frontend → Axios → FastAPI Router → Service Layer → Database → Response
```

## 배포 아키텍처

### 개발 환경
- Backend: localhost:8000
- Frontend: localhost:5173
- Database: SQLite (local file)

### 프로덕션 환경 (권장)
- Frontend: CDN (Vercel/Netlify)
- Backend: Render/Railway
- Database: PostgreSQL (Supabase/Neon)
